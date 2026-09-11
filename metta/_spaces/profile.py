"""Purpose: expose engine counter deltas and statistical profiling results.

Owns resources: _StatsBlock records a ContextVar token on entry and resets it
after reading its exit snapshot. Copied worker contexts retain independent
lifetimes [source: extensions/python/metta/_spaces/profile.py:208; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import contextlib
import html as _html
import pstats
import time
from collections import abc as _abc
from collections.abc import Sequence
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Self, cast

import metta._spaces.execution as _spaces_execution_module
import metta._spaces.handle as _spaces_handle_module
import metta._spaces.results as _spaces_results_module
import metta._spaces.scope as _spaces_scope_module
import metta._spaces.source as _spaces_source_module
import metta.doors as _doors
from metta._atoms.designation import TemplateLike
from metta._atoms.factories import Atom, Expression
from metta._atoms.templates import read_source as _read_source
from metta._binding.runtime import Runtime
from metta._errors.errors import EngineError
from metta._lazy import lazy

_SNAPSHOT_WIDTH = 10

def _without_the_interrupt_poll(
    raw: float,
    ticks: float,
    spent: float,
    at: float,
    before: float,
) -> tuple[int | float, int | float]:
    """One counter reading with the engine's interrupt poll taken out of it.

    SWI calls the seat's ``prolog:heartbeat/0`` every
    ``config.heartbeat_interval`` inferences so a Ctrl-C can reach Python
    while the engine runs, and the hook's own call ports are ordinary
    inferences in the interrupted thread. They are not the measured block's
    work, so they come out: ``spent`` is what the polls have cost this thread
    and it is subtracted from the counter.

    ``at`` is why this is exact rather than nearly right. The counter and the
    poll's tally are two reads, and no goal reads two things at one instant,
    so a tick landing between them would put its cost on one side and its
    tally on the other -- the same two inferences the subtraction exists to
    remove. The hook therefore records the counter reading it fired at, in the
    same term as the tally, and a tick recorded PAST this reading is a tick
    whose cost is not in it: `before`, what the ticks up to that one had
    spent, is subtracted instead
    [tested: test_a_reading_leaves_out_a_tick_that_fired_after_it,
    test_a_measurement_is_the_same_with_the_poll_dense].
    """
    if at > raw:
        return raw - before, ticks - 1
    return raw - spent, ticks

def _stats_snapshot(
    rt: Runtime,
) -> tuple[
    int | float,
    int | float,
    int | float,
    int | float,
    int | float,
    int | float,
    int | float,
]:
    """Read and validate the counters supplied by the engine shim."""
    raw = rt.apply_must("metta_py_stats")
    if not isinstance(raw, (list, tuple)) or len(raw) != _SNAPSHOT_WIDTH:
        msg = f"engine statistics returned an invalid snapshot: {raw!r}"
        raise EngineError(msg)
    values: list[int | float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            msg = f"engine statistics returned a non-numeric counter: {value!r}"
            raise EngineError(msg)
        values.append(value)
    inferences, ticks = _without_the_interrupt_poll(
        values[0], values[6], values[7], values[8], values[9]
    )
    return (
        inferences,
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        ticks,
    )

class _StatsBlock:
    """MeTTa.stats(): engine counter deltas over one with-block.

    After exit the fields carry the deltas the block spent: inferences
    (int), cputime (seconds), walltime (seconds, Python's perf_counter),
    gc_count, gc_freed (bytes), gc_time (seconds), table_bytes
    (answer-table bytes the block grew or, negative, released; tabling's
    memory made visible where the counters live), and heartbeats.

    `inferences` is the block's own work. The engine's interrupt poll, which
    crosses into Python every `config.heartbeat_interval` inferences so a
    Ctrl-C can land, costs inferences of its own in whatever thread the VM
    interrupts, and those are NOT the block's: they are subtracted, and
    `heartbeats` says how many times the poll ran inside the block. Without
    that subtraction two measurements of the same work differed, one time in
    eighty at the shipped interval and two times in three at a dense one
    [measured 2026-09-08: 51 of 4,000 measurements of one 659-inference
    evaluation read 667, and 2,568 of 4,000 did at an interval of 1,000;
    command=python extensions/python/benchmarks/probes/
    interrupt_poll_accounting.py --raw; commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6].

    A thread the block JOINS inside its window is counted, because SWI adds an
    exited thread's inferences to the thread that joins it, and waiting for
    that work is doing it; a detached thread finishing beside the block is not
    [measured 2026-09-08: a joined 2,000,000-inference thread moves the
    joiner's counter by 2,000,013 and a detached one by 7; command=python
    extensions/python/benchmarks/probes/interrupt_poll_accounting.py;
    commit=5f92ecfb105f7a11d8f3b1a4c0a7e3b6d4b656a6].

    A counter is a delta, so there is nothing to read before the block that
    measures it has closed, and reading one there raises rather than
    answering a number that means nothing. That also lets the counters be
    typed as the int and float they are, which is what a caller writing
    `s.inferences > 100` needs [measured 2026-08-17: it was the last
    library-caused diagnostic a downstream editor showed].
    """

    __slots__ = (
        "_before",
        "_counted",
        "_engine_inferences",
        "_rt",
        "_token",
        "_wall",
        "cputime",
        "gc_count",
        "gc_freed",
        "gc_time",
        "heartbeats",
        "inferences",
        "table_bytes",
        "walltime",
    )

    # Declared without an assignment, which __slots__ requires and which is
    # what a checker reads: the counters ARE int and float wherever they can
    # be read at all.
    inferences: int
    cputime: float
    walltime: float
    gc_count: int
    gc_freed: int
    gc_time: float
    table_bytes: int
    heartbeats: int

    def __init__(self, rt: Runtime) -> None:
        self._rt = rt
        self._counted = False
        self._engine_inferences = 0
        self._before: tuple[int | float, ...] | None = None
        self._token: Any = None
        self._wall: float | None = None

    def __getattr__(self, name: str) -> Any:
        # Reached only for a slot that was never assigned, which for a
        # counter means the block has not closed. Any other name is an
        # ordinary attribute error.
        if name in _COUNTERS:
            msg = (
                f"a stats block's {name} is the delta it measured, so it is "
                f"readable after the with-block rather than inside it"
            )
            raise RuntimeError(
                msg
            )
        msg = f"{type(self).__name__!r} object has no attribute {name!r}"
        raise AttributeError(msg, name=name, obj=self)

    def __enter__(self) -> Self:
        self._before = _stats_snapshot(self._rt)
        self._wall = time.perf_counter()
        self._token = _ACTIVE_STATS.set((*_ACTIVE_STATS.get(), self))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        before = self._before
        started_at = self._wall
        if before is None or started_at is None:
            msg = "a stats block cannot exit before it enters"
            raise RuntimeError(msg)
        wall = time.perf_counter() - started_at
        after = _stats_snapshot(self._rt)
        inferences, cputime, gc_count, gc_freed, gc_ms, table_bytes, heartbeats = (
            a - b for a, b in zip(after, before, strict=True)
        )
        # The two metta_py_stats crossings themselves sit inside the
        # window; their cost is a few hundred inferences, the noise floor.
        # AsyncMeTTa enters and exits the same block in distinct copied
        # request contexts. The entry context has already ended, so its token
        # cannot leak and cannot be reset from the exit request [tested:
        # test_aio_structural_surface_behaves; commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4].
        with contextlib.suppress(ValueError):
            _ACTIVE_STATS.reset(self._token)
        self.inferences = int(inferences) + self._engine_inferences
        self.cputime = float(cputime)
        self.walltime = wall
        self.gc_count = int(gc_count)
        self.gc_freed = int(gc_freed)
        self.gc_time = float(gc_ms) / 1000.0
        self.table_bytes = int(table_bytes)
        self.heartbeats = int(heartbeats)
        self._counted = True

    def __repr__(self) -> str:
        if not self._counted:
            return "<stats: pending>"
        return (
            f"<stats: {self.inferences} inferences, "
            f"{self.cputime:.4f}s cpu, {self.walltime:.4f}s wall>"
        )

# The counters are the block's own annotated slots, read from the class rather
# than restated: a counter added there is in this set the moment it is declared.
_COUNTERS = frozenset(_StatsBlock.__annotations__)

_ACTIVE_STATS: ContextVar[tuple[_StatsBlock, ...]] = ContextVar(
    "metta_active_stats", default=()
)

def _record_engine_inferences(count: int) -> None:
    """Add held-engine work to every enclosing stats measurement."""
    for block in _ACTIVE_STATS.get():
        block._engine_inferences += count

class EngineProfile:
    """MeTTa.profile()'s second answer: the sampler's counters and one
    row per predicate, self-ticks-descending.

    `nodes` and `top()` answer `Rows`, the same table type every other
    public door here answers, so a column is reachable by NAME rather than
    by position: `profile.nodes.predicate` and `row.ticks_self` read where
    `node[0]` and `node[3]` had to be counted out, and a notebook renders
    the profile as a table without a caller writing the header. They were
    bare tuples, which made the profile the one public answer a reader had
    to index positionally against a docstring.

    `Row` subclasses `tuple`, so positional access keeps working for
    anything that already counted.

    `seconds` is the time the sampler covered, and each row carries its
    predicate's share of it beside the raw ticks, because a tick count
    cannot be read without the ratio and nothing published the ratio. The
    conversion is the one SWI's own report prints.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("nodes", "samples", "seconds", "ticks")

    #: The sampler's own node shape, in its own order, then where the
    #: predicate was defined, what its ticks are in seconds, and the parts of
    #: the predicate the spelling in `predicate` packs together.
    #:
    #: `name` and `arity` are the predicate's own, module wrapping removed, so
    #: no reader takes `'$metta_exec:&pyspace_1':fib/2` back apart to find
    #: `fib`. `recursive_calls` is what SWI keeps on the `<recursive>`
    #: pseudo-caller: `calls` counts the ENTRIES into a directly recursive head
    #: and this counts the rest, so `calls + recursive_calls` is what the head
    #: was asked for in total.
    COLUMNS = (
        "predicate",
        "calls",
        "redos",
        "ticks_self",
        "ticks_siblings",
        "file",
        "line",
        "seconds_self",
        "seconds_total",
        "name",
        "arity",
        "recursive_calls",
    )

    def __init__(self, samples: int, ticks: int, seconds: float, nodes: list) -> None:
        self.samples = int(samples)
        self.ticks = int(ticks)
        self.seconds = float(seconds)
        self.nodes = _spaces_results_module.Rows(self.COLUMNS, nodes)

    def top(self, n: int = 10) -> _root.Rows:
        """The n predicates the samples landed in most, as `Rows`."""
        return self.nodes[:n]

    def as_stats(self) -> pstats.Stats:
        """Answer this profile as a `pstats.Stats`.

        That is the currency every Python profile viewer already reads:
        `snakeviz` and `tuna` open what `.dump_stats(path)` writes, and
        `sort_stats("cumulative")` and `print_stats()` work as they do on a
        `cProfile` run.

        The key of a pstats row is (file, line, function), so a predicate
        keeps the source location its clauses carry and a viewer can
        navigate to it. `tottime` is the predicate's own sampled seconds and
        `cumtime` adds the seconds its callees spent, which is what SWI's
        ticks_self and ticks_siblings mean.

        A predicate with no source keeps pstats' own spelling for one,
        the ('~', 0) key `func_std_string` prints bare [source: CPython
        3.14 Lib/pstats.py, func_std_string].

        Two things do not survive the format. pstats has no column for a
        REDO, so `.nodes` stays the door for choice-point cost; and the
        caller graph is left empty rather than guessed at, so a viewer shows
        a flat profile. Both are absences the format has, not measurements
        this drops.
        """
        stats: dict[tuple[str, int, str], tuple[int, int, float, float, dict]] = {
            (str(row.file) or "~", int(row.line), str(row.predicate)): (
                int(row.calls),
                int(row.calls),
                float(row.seconds_self),
                float(row.seconds_total),
                {},
            )
            for row in self.nodes
        }
        # A sampler that never fired collected nothing, which is an honest
        # profile and not a fault; pstats refuses to LOAD an empty mapping,
        # so an empty profile is built the way pstats builds an empty one.
        # typeshed narrows Stats(...) to the two profilers it ships with;
        # the argument's contract is create_stats() plus .stats, which is
        # what pstats itself reads and what _ProfileSnapshot answers.
        return (
            pstats.Stats(cast("Any", _ProfileSnapshot(stats)))
            if stats
            else pstats.Stats()
        )

    def __repr__(self) -> str:
        return (
            f"<profile: {self.samples} samples, {self.ticks} ticks, {len(self.nodes)} predicates>"
        )

class _ProfileSnapshot:
    """The profiler shape `pstats.Stats` loads from.

    `pstats.Stats(arg)` accepts an object carrying `create_stats()` and a
    `stats` dict and takes the dict away from it, which is how it reads a
    live `cProfile.Profile` [source: CPython 3.14 Lib/pstats.py, Stats.
    load_stats]. Answering that shape is the whole adapter: nothing here
    subclasses or reimplements pstats.
    """

    __slots__ = ("stats",)

    def __init__(self, stats: dict) -> None:
        self.stats = stats

    def create_stats(self) -> None:
        """Already collected; the engine sampled before this object existed."""

class Explanation(_abc.Mapping[str, Atom]):
    """The engine's decisions for one query, as the atoms `(explain ...)` answers.

        e = m.self.explain("(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))")
        e.plan          # (plan generic-join (order $_1 $_2 $_3) (relations ...))
        e["writes"]     # (writes transactional)
        list(e)         # every item head, in the engine's order

    A `Mapping` keyed by each item's HEAD, whose value is the whole item
    atom, head included, because that is the atom the engine answered. An
    explanation is data like anything else: `space.add(*e.atoms)` stores it
    and `match` queries it afterwards. A number inside an item is an ordinary
    grounded value, so `e["inferences"].children[1].value` is an `int`.

    `.atoms` is every item in the engine's own order and the mapping is the
    lookup over it. They differ when a head repeats: an operation registered
    at two arities answers two `(op ...)` items, and the mapping keeps the
    last, which is what a `{head: item}` comprehension over the MeTTa form
    keeps too. `.items()` stays Python's pairs view, inherited from `Mapping`
    and untouched.

    The plan item names the join the conjunctive matcher RUNS, not the one
    the query's shape would allow: `generic-join` appears exactly when the
    engine's Generic Join answers the pattern, so a conjunction declined for
    a non-ground stored row reads `nested-loop` like any other. `(order ...)`
    for `nested-loop` names the conjunct the matcher leads with, which is
    re-chosen at every level under the bindings above it, so it is exact
    about the first level and silent about the rest.

    The longhand is the MeTTa form: `m.run("!(explain <query>)")` answers the
    same atoms, and `analyze=True` is that run plus the `m.stats()` block
    around the query it explains.
    """

    __slots__ = ("_by_head", "analyzed", "atoms", "query")

    def __init__(self, query: Atom, atoms: Sequence[Atom], *, analyzed: bool) -> None:
        """Hold one query's items; `analyzed` says whether they were measured."""
        self.query = query
        self.atoms = tuple(atoms)
        self.analyzed = analyzed
        self._by_head = {_explanation_head(item): item for item in self.atoms}

    def __getitem__(self, head: str) -> Atom:
        return self._by_head[head]

    def __iter__(self):
        return iter(self._by_head)

    def __len__(self) -> int:
        return len(self._by_head)

    @property
    def plan(self) -> Atom | None:
        """The `(plan ...)` item, or None for a form that has no join."""
        return self._by_head.get("plan")

    @property
    def route(self) -> Atom | None:
        """The `(handles ...)` item: which seam entry takes the query.

        It carries the entry's fidelity and determinism beside it, or reads
        `(handles none)` when the engine's own unification takes the query.
        None for a form that reaches no seam at all.
        """
        return self._by_head.get("handles")

    def __rich_repr__(self):
        """rich.pretty expands an explanation by its items."""
        yield from self.atoms

    def _repr_pretty_(self, p, cycle) -> None:
        """Expand an explanation by its items for IPython's printer."""
        if cycle:
            p.text("<explanation ...>")
            return
        with p.group(2, "<explanation ", ">"):
            for index, item in enumerate(self.atoms):
                if index:
                    p.breakable()
                p.pretty(item)

    def _repr_html_(self) -> str:
        """Notebook display: one row per item, its head beside its arguments."""
        rows = "".join(
            f"<tr><td><b>{_html.escape(head)}</b></td>"
            f"<td>{_html.escape(' '.join(str(child) for child in _explanation_rest(item)))}</td></tr>"
            for head, item in self._by_head.items()
        )
        measured = " (analyzed)" if self.analyzed else ""
        return (
            "<table style='font-family: monospace; border-collapse: collapse;'>"
            f"<caption>explain {_html.escape(str(self.query))}{measured}</caption>"
            f"<tbody>{rows}</tbody></table>"
        )

    def __repr__(self) -> str:
        measured = ", analyzed" if self.analyzed else ""
        return f"<explanation of {self.query} ({len(self.atoms)} items{measured})>"

def _explanation_head(item: Atom) -> str:
    """The item's head, which is the mapping key it arrives under."""
    if isinstance(item, Expression) and item.children:
        return str(item.children[0])
    return str(item)

def _explanation_rest(item: Atom) -> tuple[Atom, ...]:
    """Everything the item says after its head."""
    return item.children[1:] if isinstance(item, Expression) else ()

class FunctionCost:
    """One registered function's row in MeTTa.profile_extension().

    `calls` and `redos` are counted rather than sampled, so they are exact;
    `ticks` is the sampler's and carries its uncertainty. A `redo` is the
    engine re-entering the predicate for another answer, which is what a
    left-behind choice point looks like from outside: a function meant to be
    deterministic showing redos is the signal to look for a missing cut or
    an unindexed head.

    `speedup` is the ratio SWI computes for the clause index it chose, so
    1.0 means no argument discriminates and every call walks the clause
    list. `indexed` says whether the index exists yet: SWI builds one on
    first need, so False on a predicate nothing has called enough times is
    an absent index rather than a bad one.
    """

    __slots__ = (
        "arity",
        "calls",
        "determinism",
        "indexed",
        "name",
        "redos",
        "source",
        "speedup",
        "ticks",
        "tier",
    )

    # Keyword-only, which the one call site already does and which is what
    # makes ten fields safe: calls, redos and ticks are three adjacent ints
    # nothing would catch transposed.
    def __init__(
        self,
        *,
        name: str,
        tier: str,
        source: str,
        arity: int | None,
        calls: int,
        redos: int,
        ticks: int,
        speedup: float,
        indexed: bool,
        determinism: str,
    ) -> None:
        self.name = name
        self.tier = tier
        self.source = source
        self.arity = arity
        self.calls = calls
        self.redos = redos
        self.ticks = ticks
        self.speedup = speedup
        self.indexed = indexed
        # What the library DECLARED, empty when it declared nothing. Read the
        # redos against it: a redo on a nondet function is the function
        # working, and one on a function declaring nothing is a question.
        self.determinism = determinism

    def __repr__(self) -> str:
        return (
            f"<{self.name}/{self.arity} {self.tier}: {self.calls} calls, "
            f"{self.redos} redos, {self.ticks} ticks, index {self.speedup:g}x"
            + (f", declared {self.determinism}>" if self.determinism else ">")
        )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_exports_as_pstats', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_is_the_same_table_every_other_door_answers', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_counts_samples_on_real_work'),
)
def profile(
    space: _root.Space,
    source: str | TemplateLike,
    /,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    **values: Any,
) -> tuple[list[list[Atom]], EngineProfile]:
    """Run source under the engine's statistical profiler, answering
    (groups, profile): the groups exactly as run() answers them, and
    the profile carrying sample counters plus one row per predicate,
    self-ticks first.

        groups, prof = m.profile("!(big-computation)")
        prof.top(5)     # the five predicates the samples landed in

    A row carries the predicate's calls and redos, its ticks, the file
    and line its clauses were defined at, and its share of the sampled
    seconds. `prof.as_stats()` answers the same run as a `pstats.Stats`,
    so `sort_stats("cumulative").print_stats()` reads it and
    `dump_stats(path)` writes what snakeviz and tuna open.

    The sampler is statistical: a program that finishes in
    milliseconds carries few samples, so profile something that runs.
    Profiling changes execution; it is a debugging surface, not a
    mode to leave on.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    source, holes = _read_source(
        source, values, called="profile", reserved=_spaces_execution_module._SOURCE_KEYWORDS
    )
    return _spaces_execution_module.profile_source(
        space._rt,
        space._space,
        source,
        _spaces_source_module._with_holes(_spaces_scope_module._RUN_BINDINGS.get(), holes),
        timeout=timeout,
        inferences=inferences,
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.tuple,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_needs_exactly_one_of_extension_or_names', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_reports_every_declared_member', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_profile_extension_separates_an_indexed_table_from_a_single_clause'),
    refuses=(_doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_door_value_refusals[space:profile-extension]'),),
)
def profile_extension(
    space: _root.Space,
    source: str | TemplateLike,
    /,
    *,
    extension: str | None = None,
    names: _abc.Sequence[str] | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
    **values: Any,
) -> tuple[list[list[Atom]], list[FunctionCost]]:
    """Run source under the profiler, reporting only YOUR functions.

    `profile()` answers "which predicate did the samples land in", over
    every predicate in the process. The question a library author has is
    narrower: of the functions my library registered, which one is
    costing me, and is anything wrong with how it was installed.

        groups, costs = m.profile_extension("!(my-workload)",
                                            extension="mylib")
        for cost in costs:
            print(cost)
        # <mylib-join/3 prolog: 40100 calls, 39900 redos, 812 ticks, index 1x>

    Name the `extension` and its registered members are looked up, or
    pass `names` for an explicit list. Each row carries the tier that
    installed the function and where from, its exact call and redo
    counts, the sampler's ticks, and its clause index.

    The two columns worth reading first are `redos` and `speedup`. Redos
    on a function meant to be deterministic are a leftover choice point,
    which costs the caller about twice and is invisible to the inference
    counter. A `speedup` of 1 means no argument discriminates, so every
    call walks the clause list; `indexed` False on a function nothing has
    called much only means SWI has not built one yet.

    The sampler is statistical, so profile something that runs, and
    profiling changes execution: this is a debugging surface.
    """
    if (extension is None) == (names is None):
        msg = (
            "profile_extension takes extension= (its registered members) "
            "or names= (an explicit list), and needs exactly one of them"
        )
        raise ValueError(
            msg
        )
    wanted = (
        [str(name) for name in names]
        if names is not None
        else list(_extension_members(space, extension))
    )
    source, holes = _read_source(
        source, values, called="profile_extension", reserved=_spaces_execution_module._EXTENSION_KEYWORDS
    )
    return _spaces_execution_module.profile_extension(
        space._rt,
        space._space,
        source,
        _spaces_source_module._with_holes(_spaces_scope_module._RUN_BINDINGS.get(), holes),
        wanted,
        timeout=timeout,
        inferences=inferences,
    )

def _extension_members(space: _root.Space, extension: str | None) -> tuple[str, ...]:
    _spaces_handle_module._require_name(extension, "profile_extension")
    return tuple(
        space._rt.must(
            "metta_py_extension_members(Name, Names)", Name=str(extension)
        )["Names"]
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.context,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch14_seeing_your_program/test_explain_plan.py::test_analyze_numbers_equal_the_stats_of_the_same_query', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_profile_exports_as_pstats', 'extensions/python/tests/ch14_seeing_your_program/test_features.py::test_a_stats_counter_is_unreadable_until_its_block_closes'),
    alias='stats',
)
def stats(space: _root.Space) -> _StatsBlock:
    """The engine's own counters over a with-block, as deltas.

        with m.stats() as s:
            m.match(S.edge(V.x, V.y), S.edge(V.y, V.z))
        s.inferences        # engine steps the block spent
        s.cputime           # engine CPU seconds
        s.walltime          # wall seconds, Python's clock
        s.gc_count, s.gc_freed, s.gc_time
        s.table_bytes       # answer-table bytes grown, tabling's memory

    The counters are SWI's statistics/2 read on the CALLING thread, so
    a block that runs other threads' engine work counts that work too;
    the honest reading is "what this thread saw the engine do while the
    block ran". A lazy cursor is the exception, and a large one: its
    goal runs in an SWI engine, an engine counts its own inferences,
    and this thread cannot see them. Draining 20,000 rows through the
    match cursor reports 40,049 inferences against about 381,000 the
    cursor's engine really spent, 10.5% of the work; the real cost is
    readable off the `inferences` budget, which does count the engine
    [measured 2026-08-27]. The evaluation cursor behind `answers()`
    does report its engine's spend, so that one is whole. The z3py
    Solver.statistics() reading, on the engine this library actually
    has.
    """
    return _StatsBlock(space._rt)

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
