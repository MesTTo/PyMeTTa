"""Purpose: query, profiling, scope, and callable objects returned by MeTTa.
Guarantees:
  - scoped timeout, inference, and stack-byte bounds are task-local and stack
    bounds select ``petta_py_limited/6`` while the unbounded path preserves
    ``petta_py_limited/5`` [tested:
    test_stack_limit_is_carried_to_the_limited_six_seam; commit=WORKTREE]
  - Cursor keeps exhaustion distinct from explicit close [tested
    test_stream_agrees_with_query_and_closes_on_exhaustion]
  - Prepared preserves first-appearance query columns [tested
    test_query_surfaces_share_column_order]
  - the bound function namespace transliterates attributes, preserves exact
    bracket names, resolves a trailing bang, and rejects unknown names at
    access [tested: test_bound_function_namespace_validates_at_access;
    commit=2d4d4583c2d82e90bb21a7e8671842f126edd4f4]
  - bound function attributes consult the operator word table before the
    mechanical map [tested: test_operator_words_precede_the_mechanical_name_map;
    commit=WORKTREE]
  - a resolved bang call completes before the call returns while retaining a
    replayable answer view [tested: test_resolved_bang_call_is_eager;
    commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - resolved bang mutations invalidate the owning space's builtin catalogue
    [tested: test_builtin_cache_invalidates_after_a_miss; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
Owns:
  - Cursor owns one engine query until exhaustion, close, or finalization
    and warns when finalization reaps an open query [tested
    test_abandoned_stream_warns_before_reaping]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import contextlib
import inspect
import logging
import time
import warnings
import weakref
from collections.abc import Iterable
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Self, cast

from ._engine import Runtime
from ._name_mapping import operator_attribute_target
from .atoms import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _atom_from_wire,
    _decode,
    _encode,
    _to_atom,
    _variables,
)
from .errors import EngineError, PettaError
from .results import Rows, _row_class

if TYPE_CHECKING:
    from ._space import Space as MeTTa

logger = logging.getLogger(__name__)


def _require_bound(value: Any, called: str, kinds: tuple[type, ...], reads: str) -> None:
    """Check one per-call bound, type before magnitude.

    Comparing first reports a wrong type as "'>' not supported between
    instances of 'str' and 'int'", which names neither the argument nor the
    call the user made.
    """
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, kinds):
        msg = f"{called} must be {reads} or None, got {value!r}"
        raise TypeError(msg)
    # isinstance against a variable tuple narrows value to object, so the
    # comparison needs the type the check just established.
    if not cast(float, value) > 0:
        msg = f"{called} must be positive, got {value!r}"
        raise ValueError(msg)


#: The scoped defaults `with m.limits(...)` sets: a contextvar, so the
#: scope is async-correct and thread-local the way decimal.localcontext
#: is. Per-call kwargs override by simply not being None.
_SCOPED_LIMITS: ContextVar[tuple[float | None, int | None, int | None]] = ContextVar(
    "petta_scoped_limits", default=(None, None, None)
)


class ScopedLimits:
    """The with-block m.limits() answers: sets the scoped defaults on
    entry, restores the previous scope on exit, exceptions included.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(
        self,
        timeout: float | None,
        inferences: int | None,
        stack: int | None,
    ) -> None:
        _require_bound(timeout, "timeout", (int, float), "seconds as a number")
        _require_bound(inferences, "inferences", (int,), "a positive int")
        _require_bound(stack, "stack", (int,), "a positive byte count")
        self._value = (timeout, inferences, stack)
        self._token: Any = None

    def __enter__(self) -> Self:
        self._token = _SCOPED_LIMITS.set(self._value)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _SCOPED_LIMITS.reset(self._token)


def _limits(
    timeout: float | None,
    inferences: int | None,
    stack: int | None = None,
) -> tuple[float, int, int] | None:
    """Validate the per-call bounds into the shim's ``-1 = none`` triple.
    A bound the call did not name falls back to the scoped default
    m.limits() set, which is how one with-block replaces a parameter
    forest while every per-call kwarg still overrides.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if timeout is None or inferences is None or stack is None:
        scoped_timeout, scoped_inferences, scoped_stack = _SCOPED_LIMITS.get()
        if timeout is None:
            timeout = scoped_timeout
        if inferences is None:
            inferences = scoped_inferences
        if stack is None:
            stack = scoped_stack
    if timeout is inferences is stack is None:
        return None
    _require_bound(timeout, "timeout", (int, float), "seconds as a number")
    _require_bound(inferences, "inferences", (int,), "a positive int")
    _require_bound(stack, "stack", (int,), "a positive byte count")
    return (
        -1.0 if timeout is None else float(timeout),
        -1 if inferences is None else int(inferences),
        -1 if stack is None else int(stack),
    )


def _apply_limited(
    runtime: Runtime,
    limits: tuple[float, int, int],
    predicate: str,
    inputs: list[Any],
) -> Any:
    """Apply the preserved /5 seam or stack-aware /6 seam as required."""
    seconds, steps, stack = limits
    if stack < 0:
        return runtime.apply_must(
            "petta_py_limited", seconds, steps, predicate, inputs
        )
    return runtime.apply_must(
        "petta_py_limited", seconds, steps, stack, predicate, inputs
    )


def guard_atom(where: Any | None) -> Atom | None:
    """Convert a where= guard, refusing one that can never answer a truth.

    A grounded non-boolean is the trap: it converts to a perfectly good
    atom, the engine evaluates it per row, nothing is ever true, and the
    query answers empty as though the data were wrong. why() then blames
    the guard, which is honest but sends the reader to the data.
    """
    if where is None:
        return None
    guard = _to_atom(where)
    # An expression is the guard proper; a variable is one a pattern bound to
    # a truth; a grounded bool is trivially one. A grounded value or a bare
    # symbol is neither a call nor a truth, so it can never be true.
    if isinstance(guard, (Expression, Variable)):
        return guard
    if isinstance(guard, Grounded) and isinstance(guard.value, bool):
        return guard
    msg = (
        f"a where= guard is a term the engine evaluates per row, as in "
        f"(V.age >= 18); {where!r} can never answer true"
    )
    raise TypeError(
        msg
    )


def _stats_snapshot(
    rt: Runtime,
) -> tuple[
    int | float,
    int | float,
    int | float,
    int | float,
    int | float,
    int | float,
]:
    """Read and validate the six counters supplied by the engine shim."""
    raw = rt.apply_must("petta_py_stats")
    if not isinstance(raw, (list, tuple)) or len(raw) != 6:
        msg = f"engine statistics returned an invalid snapshot: {raw!r}"
        raise EngineError(msg)
    values: list[int | float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            msg = f"engine statistics returned a non-numeric counter: {value!r}"
            raise EngineError(msg)
        values.append(value)
    return values[0], values[1], values[2], values[3], values[4], values[5]


def _column_names(atoms: Iterable[Atom]) -> list[str]:
    """Distinct non-anonymous variables in first-appearance order."""
    return list(dict.fromkeys(name for atom in atoms for name in _variables(atom) if name != "_"))


class _Assuming:
    """Facts scoped to a with-block; see MeTTa.assuming."""

    __slots__ = ("_facts", "_space")

    def __init__(self, space: MeTTa, facts: list[Atom]) -> None:
        self._space = space
        self._facts = facts

    def __enter__(self) -> MeTTa:
        self._space.add(*self._facts)
        return self._space

    def __exit__(self, exc_type, exc, tb) -> None:
        for fact in self._facts:
            self._space.remove(fact)


#: The counters a stats block fills on exit, named here so __getattr__ can
#: tell "read too early" from an ordinary typo.
_COUNTERS = frozenset(
    {
        "inferences",
        "cputime",
        "walltime",
        "gc_count",
        "gc_freed",
        "gc_time",
        "table_bytes",
    }
)


class _StatsBlock:
    """MeTTa.stats(): engine counter deltas over one with-block.

    After exit the fields carry the deltas the block spent: inferences
    (int), cputime (seconds), walltime (seconds, Python's perf_counter),
    gc_count, gc_freed (bytes), gc_time (seconds), and table_bytes
    (answer-table bytes the block grew or, negative, released; tabling's
    memory made visible where the counters live).

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
        raise AttributeError(msg)

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
        inferences, cputime, gc_count, gc_freed, gc_ms, table_bytes = (
            a - b for a, b in zip(after, before, strict=True)
        )
        # The two petta_py_stats crossings themselves sit inside the
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
        self._counted = True

    def __repr__(self) -> str:
        if not self._counted:
            return "<stats: pending>"
        return (
            f"<stats: {self.inferences} inferences, "
            f"{self.cputime:.4f}s cpu, {self.walltime:.4f}s wall>"
        )


_ACTIVE_STATS: ContextVar[tuple[_StatsBlock, ...]] = ContextVar(
    "petta_active_stats", default=()
)


def _record_engine_inferences(count: int) -> None:
    """Add held-engine work to every enclosing stats measurement."""
    for block in _ACTIVE_STATS.get():
        block._engine_inferences += count


def _forward_window(window: slice) -> tuple[int, int | None]:
    """A cursor slice's bounds, refusing the ones that need the whole stream.

    Both refusals are the design. A step still PULLS the rows it skips, and a
    negative bound means knowing where the end is, so accepting either would
    quietly buy the full scan the cursor exists to avoid, in the spelling that
    looks cheapest.
    """
    if window.step is not None and window.step != 1:
        msg = (
            "a cursor slice takes no step: skipping rows still pulls them, "
            "so [::2] costs what taking them all costs"
        )
        raise ValueError(
            msg
        )
    start = 0 if window.start is None else window.start
    if start < 0 or (window.stop is not None and window.stop < 0):
        msg = (
            "a cursor slice counts from the start only: a negative bound "
            "needs the whole stream, which is what the cursor exists to avoid"
        )
        raise ValueError(
            msg
        )
    return start, window.stop


def _explain_text(rt: Runtime, space_name: str, patterns: list, where) -> str:
    """The seam's own decisions for one conjunction, rendered. Pure
    reflection through petta_py_explain: nothing runs, no row is pulled,
    and the engine answers claimed/rest as indexes so the caller's own
    atoms, variable names included, do the rendering.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    kind, detail, claimed, rest = rt.apply_must(
        "petta_py_explain", space_name, [p.to_wire() for p in patterns]
    )
    shown = ", ".join(str(p) for p in patterns)
    lines = [f"query over {space_name}: {shown}"]
    if kind == "stored":
        lines.append("  stored atoms: engine unification joins the conjunction left to right")
    elif kind == "refused":
        lines.append(f"  REFUSED: the declared entry {detail[0]} answers Refuse for this conjunction")
    else:
        width = max(len(str(p)) for p in patterns)
        for pattern, (klass, origin) in zip(patterns, detail, strict=True):
            lines.append(f"  {pattern!s:<{width}}  {klass:<8}  {origin}")
        if claimed:
            names = ", ".join(str(patterns[i]) for i in claimed)
            lines.append(f"  conjunction: the provider claimed {names}")
            if rest:
                joined = ", ".join(str(patterns[i]) for i in rest)
                lines.append(f"  the engine joins the rest: {joined}")
            else:
                lines.append("  the engine joins nothing further")
        elif len(patterns) > 1:
            lines.append("  conjunction: no provider claim; the engine joins left to right")
        if any(k == "exact" for k, _ in detail):
            lines.append("  a bound reaches the provider only where the class is exact")
    if where is not None:
        lines.append(f"  guard {where}: runs in the engine over each row")
    return "\n".join(lines)


_CURSOR_LENGTH_REFUSAL = (
    "a cursor has no len(): counting its rows means pulling all of them, "
    "which is what it exists to avoid. Use len(space.query(pattern)) for the "
    "count, or query() if you want the rows"
)


class Cursor:
    """Private streaming answers pulled one at a time from an engine-held
    query. Iterate it, close() it, or leave its with-block. Exhaustion reaps
    the engine and remains ordinary iterator exhaustion; explicit close is a
    separate state that refuses further pulls. A cursor dropped unclosed is
    reaped by its finalizer. Rows carry the query's variable names as columns,
    exactly as query()'s rows do.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = (
        "__weakref__",
        "_atoms",
        "_closed",
        "_exhausted",
        "_finalizer",
        "_handle",
        "_row_cls",
        "_rt",
        "_space_name",
        "_stack",
        "_timeout",
        "_where_atom",
        "columns",
    )

    def __init__(
        self,
        space: MeTTa,
        patterns: tuple,
        where: Any | None,
        timeout: float | None,
        inferences: int | None,
        *,
        limit: int | None = None,
    ) -> None:
        atoms = [_to_atom(p) for p in patterns]
        columns = _column_names(atoms)
        self.columns = tuple(columns)
        self._row_cls = _row_class(self.columns)
        limits = _limits(timeout, inferences)
        # The inference budget rides inside the engine (its work is its
        # own counter's, invisible to a per-pull wrapper); the wall bound
        # wraps each pull outside, where idle time between pulls is free.
        self._timeout = None if limits is None or limits[0] < 0 else limits[0]
        steps = -1 if limits is None else limits[1]
        self._stack = -1 if limits is None else limits[2]
        self._rt = space.runtime
        self._atoms = atoms
        self._space_name = space.name
        wires = [a.to_wire() for a in atoms]
        checked = guard_atom(where)
        self._where_atom = checked
        guard = [] if checked is None else checked.to_wire()
        self._handle = self._rt.apply_must(
            "petta_py_cursor_open",
            space.name,
            wires,
            guard,
            columns.copy(),
            limit or 0,
            steps,
        )
        self._closed = False
        self._exhausted = False
        # The finalizer is the last guard, not the contract: it destroys
        # the engine if a cursor is dropped unclosed, from whichever
        # thread collection runs on (cross-thread destroy is probed).
        self._finalizer = weakref.finalize(self, Cursor._reap, self._rt, self._handle)

    @staticmethod
    def _reap(runtime: Runtime, handle: Any) -> None:
        try:
            runtime.do("petta_py_cursor_close", handle)
        except EngineError:
            logger.debug("cursor finalization found an unavailable engine", exc_info=True)

    def __iter__(self) -> Self:
        return self

    def __next__(self):
        if self._exhausted:
            raise StopIteration
        if self._closed:
            msg = "this cursor is closed"
            raise PettaError(msg)
        if self._timeout is None and self._stack < 0:
            answer = self._rt.apply_must("petta_py_cursor_next", self._handle)
        else:
            answer = _apply_limited(
                self._rt,
                (-1.0 if self._timeout is None else self._timeout, -1, self._stack),
                "petta_py_cursor_next",
                [self._handle],
            )
        if not answer:
            self._exhausted = True
            self._finalizer()
            raise StopIteration
        return self._row_cls(_atom_from_wire(v) for v in answer[0])

    def explain(self) -> str:
        """The query's plan, reflected rather than run: which provider
        decisions the seam already made for this conjunction. See
        Prepared.explain for the whole story; a cursor explains the same
        way, and explaining does not pull a row.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _explain_text(self._rt, self._space_name, self._atoms, self._where_atom)

    def __getitem__(self, index: int | slice):
        """`cursor[:3]` and `cursor[0]`, pulling only what is asked for.

        This is the one convenience worth adding here, because it changes the
        SPELLING and not the plan. Measured over 2,000 stored atoms, wanting
        the first three: `query(pat)[:3]` costs 26,049 inferences because
        slicing trims after computing everything, `query(pat, limit=3)` costs
        94, and pulling three from a cursor costs 13. The cheapest route was
        the only one that could not be spelled naturally.

        A negative index or a step is REFUSED, not supported. Both need the
        whole stream, so accepting them would quietly buy the 26,049
        inferences this exists to avoid, in the spelling that looks cheapest.
        """
        if isinstance(index, slice):
            return self._take_slice(index)
        if not isinstance(index, int):
            msg = (
                f"a cursor is indexed by an int or a slice, not "
                f"{type(index).__name__}"
            )
            raise TypeError(
                msg
            )
        if index < 0:
            msg = (
                "a cursor cannot be indexed from the end: it does not know "
                "where the end is without pulling every row, which is what "
                "the cursor exists to avoid. Use query() if you want them all"
            )
            raise IndexError(
                msg
            )
        for position, row in enumerate(self):
            if position == index:
                return row
        msg = f"the cursor answered fewer than {index + 1} rows"
        raise IndexError(msg)

    def _take_slice(self, window: slice) -> list:
        start, stop = _forward_window(window)
        if stop is not None and stop <= start:
            return []
        taken = []
        for position, row in enumerate(self):
            if position >= start:
                taken.append(row)
            if stop is not None and position + 1 >= stop:
                break
        return taken

    def __len__(self) -> int:
        """Refused, and the refusal is the design.

        A length cannot be known without consuming the cursor, so answering
        one would silently materialise the very thing the cursor exists to
        avoid.
        """
        raise TypeError(_CURSOR_LENGTH_REFUSAL)

    def close(self) -> None:
        """Destroy the held engine; idempotent and distinct from exhaustion."""
        if self._closed or self._exhausted:
            return
        self._closed = True
        self._finalizer()  # runs the reap exactly once; later GC is a no-op

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        if not getattr(self, "_closed", True) and not getattr(self, "_exhausted", True):
            warnings.warn(
                "an open petta Cursor was discarded; use a with-block or close()",
                ResourceWarning,
                source=self,
                stacklevel=2,
            )

    def __repr__(self) -> str:
        state = "closed" if self._closed else "exhausted" if self._exhausted else "open"
        return f"<cursor {state} -> {', '.join(self.columns)}>"


class EngineProfile:
    """MeTTa.profile()'s second answer: the sampler's counters and one
    row per predicate, self-ticks-descending. Each node is (predicate,
    calls, redos, ticks_self, ticks_siblings).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("nodes", "samples", "ticks")

    def __init__(self, samples: int, ticks: int, nodes: list) -> None:
        self.samples = int(samples)
        self.ticks = int(ticks)
        self.nodes = [tuple(node) for node in nodes]

    def top(self, n: int = 10) -> list[tuple]:
        """The n predicates the samples landed in most."""
        return self.nodes[:n]

    def __repr__(self) -> str:
        return (
            f"<profile: {self.samples} samples, {self.ticks} ticks, {len(self.nodes)} predicates>"
        )


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


class Prepared:
    """A prepared query: pattern wires and columns built once, solved many
    times, optionally with per-call facts. The ladder the clingo API walks
    (assumptions per solve, inputs per session, rules added), with the rung
    clingo lacks: rules REMOVED, since this engine erases clauses whole.

        route = m.prepare(S.path(V.a, V.b))
        route.solve()
        route.solve(given=[S.edge(S.a, S.b)])   # facts for this call only
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_guard", "_patterns", "_space", "_where", "_wires", "columns")

    def __init__(self, space: MeTTa, patterns: list[Atom], where: Atom | None) -> None:
        self._space = space
        self._patterns = patterns
        self._where = where
        self._wires = [p.to_wire() for p in patterns]
        self._guard = None if where is None else where.to_wire()
        self.columns = tuple(_column_names(patterns))

    def solve(
        self,
        given: list | None = None,
        limit: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Rows:
        """Answers now, with `given` facts present for this call alone.
        `timeout` and `inferences` bound this solve exactly as they bound
        MeTTa.query().
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if not given:
            return self._run(limit, timeout, inferences)
        with self._space.assuming(*given):
            return self._run(limit, timeout, inferences)

    def _run(self, limit: int | None, timeout: float | None, inferences: int | None) -> Rows:
        rt = self._space.runtime
        space = self._space.name
        names = list(self.columns)
        if self._guard is not None:
            pred = "petta_py_query_guarded_all"
            ins = [space, self._wires, self._guard, names, limit or 0]
        elif limit is not None:
            pred, ins = "petta_py_query_limit_all", [space, self._wires, names, limit]
        else:
            pred, ins = "petta_py_query_all", [space, self._wires, names]
        limits = _limits(timeout, inferences)
        if limits is None:
            answered = rt.apply_must(pred, *ins)
        else:
            answered = _apply_limited(rt, limits, pred, ins)
        decoded = [tuple(_atom_from_wire(v) for v in r) for r in answered]
        return Rows(self.columns, decoded)

    def explain(self) -> str:
        """The query's plan, reflected rather than run: polars'
        LazyFrame.explain and SQL's EXPLAIN, from decisions the seam has
        already made. For a Python-backed space, each pattern's line says
        whether its candidates push down exact (the provider's answers
        are trusted as instantiations, a bound may reach it) or inexact
        (candidates re-unify in the engine), and which rule decided:
        a declared (handles ...) entry, the provider's own pushdown
        method, or silence. A conjunction line names what a planning
        provider claimed whole and what the engine joins. Stored spaces
        answer the one true line: engine unification. No row is pulled
        and no provider match is called; the provider's plan hook is
        consulted exactly as a real query would consult it, since the
        claim is the provider's to make.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _explain_text(self._space.runtime, self._space.name, self._patterns, self._where)

    def __repr__(self) -> str:
        shown = ", ".join(str(p) for p in self._patterns)
        return f"<prepared {shown} -> {', '.join(self.columns)}>"


_UNDEFINED_TYPE = Symbol("%Undefined%")


def _doc_text(atom: object) -> str:
    """The prose inside a doc part: a string value decodes, anything
    else renders as written.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(atom, Grounded):
        value = _decode(atom)
        if isinstance(value, str):
            return value
    return str(atom)


def _format_doc_atom(doc: Expression) -> str:
    """`(@doc name (@desc ...) (@params (...)) (@return ...))` as help()
    text: one summary line, then the parameters, then the return.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    name = doc.children[1] if len(doc.children) > 1 else ""
    lines: list[str] = []
    parameters: list[str] = []
    returns: str | None = None
    for part in doc.children[2:]:
        if not (isinstance(part, Expression) and part.children):
            continue
        head, *rest = part.children
        if head == Symbol("@desc") and rest:
            lines.append(f"{name}: {_doc_text(rest[0])}")
        elif head == Symbol("@params") and rest and isinstance(rest[0], Expression):
            parameters = [
                _doc_text(param.children[1])
                for param in rest[0].children
                if isinstance(param, Expression) and len(param.children) > 1
            ]
        elif head == Symbol("@return") and rest:
            returns = _doc_text(rest[0])
    if not lines:
        lines.append(str(name))
    if parameters:
        lines.extend(("", "Parameters:"))
        lines.extend(f"  - {parameter}" for parameter in parameters)
    if returns is not None:
        lines.append(f"Returns: {returns}")
    return "\n".join(lines)


class _EngineFunction:
    """One engine function, callable the way Python callables are.

    Beyond calling, it carries the function protocol's introspection:
    __name__ and __qualname__ as data, __doc__, __signature__, .type,
    .equations and .compiled as live reads of the space, so help() and
    inspect.signature() answer from MeTTa's own declarations.
    functools.partial composes because this is an ordinary callable,
    which is the whole bound-method story; there is deliberately no
    __defaults__ or __annotations__, because MeTTa has no default
    arguments and the annotations live on the arrow type.
    """

    # A slot named __qualname__ is the one pure-Python spelling of
    # method.__qualname__'s C getset: the member descriptor answers per
    # instance, while class access keeps resolving through the
    # type.__qualname__ metaclass data descriptor, so the class still
    # answers _EngineFunction (verified in test_name_and_qualname_...).
    # Assigning a property after class creation is refused by that same
    # metaclass setter, which only accepts str. pylint flags the
    # shadowing it cannot see resolves correctly.
    __slots__ = (
        "__name__",
        "__qualname__",  # pylint: disable=class-variable-slots-conflict
        "_name",
        "_space",
    )

    def __init__(self, space: MeTTa, name: str) -> None:
        self._space = space
        self._name = name
        self.__name__ = name
        self.__qualname__ = f"{space.name}.{name}"

    def _term(self, args: tuple) -> Expression:
        return Expression([Symbol(self._name), *(_encode(a) for a in args)])

    def __call__(self, *args: Any) -> Any:
        """Evaluate this call and return its replayable Answers.

        MeTTa's trailing ``!`` is its effect marker, not a Python convention
        invented by this namespace.  A resolved bang name therefore drains
        at the call boundary so the statement has happened when its line
        completes.  Non-bang calls retain demand-driven evaluation.
        """
        answers = self._space.answers(self._term(args))
        if self._name.endswith("!"):
            answers._materialize()
            self._space._invalidate_builtins()
        return answers

    # ------------------------------------------------------- introspection

    @property
    def type(self) -> Atom | None:
        """The declared type atom, or None when undeclared.

        get-type's own answer through this space's context, so a named
        space's declarations count; %Undefined% reads as None because
        the function protocol spells absence that way. MeTTa allows
        several declarations for one name; this answers the first.
        """
        answers = self._space.eval(Expression([Symbol("get-type"), Symbol(self._name)]))
        for answer in answers:
            if isinstance(answer, Atom) and answer != _UNDEFINED_TYPE:
                return answer
        return None

    @property
    def equations(self) -> list[Expression]:
        """The stored `(= (f ...) body)` atoms, live from the space."""
        wires = self._space._rt.apply_must(
            "petta_py_equations", self._space.name, self._name
        )
        return [cast(Expression, _atom_from_wire(w)) for w in wires]

    @property
    def compiled(self) -> str:
        """The Prolog clauses this name compiled to: dis for the
        translator, exposed from the function handle as a property.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._space._disassemble(self._name)

    @property
    def __signature__(self) -> inspect.Signature:
        """Built from the arrow type when one is declared, so
        inspect.signature() and completion show the arity with the
        parameter types as annotations; no arrow means (*args).
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        arrow = self.type
        if (
            not isinstance(arrow, Expression)
            or not arrow.children
            or arrow.children[0] != Symbol("->")
        ):
            return inspect.Signature(
                [inspect.Parameter("args", inspect.Parameter.VAR_POSITIONAL)]
            )
        parts = arrow.children[1:]
        parameters = [
            inspect.Parameter(
                f"x{position}",
                inspect.Parameter.POSITIONAL_ONLY,
                annotation=str(part),
            )
            for position, part in enumerate(parts[:-1], start=1)
        ]
        return inspect.Signature(
            parameters, return_annotation=str(parts[-1]) if parts else ""
        )

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        """MeTTa's own documentation, formatted for help(): the space's
        `(@doc name ...)` atom when one exists (the engine's register
        documents every prelude form, so builtins answer too), else the
        declaration and equations, else None as Python spells absence.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        answers = self._space.eval(Expression([Symbol("get-doc"), Symbol(self._name)]))
        if answers and isinstance(answers[0], Expression):
            return _format_doc_atom(answers[0])
        lines = []
        declared = self.type
        if declared is not None:
            lines.append(f"{self._name}: {declared}")
        equations = self.equations
        if equations:
            if not lines:
                lines.append(self._name)
            lines.extend(("", "Equations:"))
            lines.extend(f"  {equation}" for equation in equations)
        return "\n".join(lines) if lines else None

    def __repr__(self) -> str:
        return f"<engine function {self._name} on {self._space.name}>"


class _FunctionNamespace:
    """Functions visible to one space, resolved when an attribute is read.

    MeTTa marks effects with a trailing ``!``.  Calls whose resolved name has
    that marker execute eagerly at the call door; all other calls stay lazy.
    """

    __slots__ = ("_space",)

    def __init__(self, space: MeTTa) -> None:
        self._space = space

    def _known(self, name: str) -> bool:
        return name in self._space.builtins() or self._space.is_function_here(name)

    def _resolve(self, name: str, *, attribute: str | None = None) -> _EngineFunction:
        resolved = name
        if not self._known(resolved):
            bang = f"{resolved}!"
            if attribute is not None and self._known(bang):
                resolved = bang
            else:
                asked = attribute if attribute is not None else name
                msg = f"{self._space.name}.fn has no function {asked!r}"
                raise AttributeError(msg)
        return _EngineFunction(self._space, resolved)

    def __getattr__(self, name: str) -> _EngineFunction:
        if name.startswith("_"):
            raise AttributeError(name)
        resolved = operator_attribute_target(name)
        target = name.replace("_", "-") if resolved is None else resolved
        return self._resolve(target, attribute=name)

    def __getitem__(self, name: str) -> _EngineFunction:
        if not isinstance(name, str) or not name:
            msg = f"a function name must be a nonempty str, got {name!r}"
            raise TypeError(msg)
        return self._resolve(name)

    def __dir__(self) -> list[str]:
        names = {
            name.removesuffix("!").replace("-", "_")
            for name in self._space.builtins()
            if name and name.replace("-", "_").removesuffix("!").isidentifier()
        }
        return sorted(set(super().__dir__()) | names)

    def __repr__(self) -> str:
        return f"<function namespace for {self._space.name}>"


#: Active batch collectors by space name; a contextvar mapping, so a
#: batch region is task-scoped exactly as limits() scopes are. The
#: default mapping is never mutated: entering copies.
_EMPTY_BATCHES: dict[str, list] = {}  # never mutated; entering copies
_ACTIVE_BATCHES: ContextVar[dict[str, list]] = ContextVar(
    "petta_active_batches", default=_EMPTY_BATCHES
)


def _refuse_in_batch(space_name: str, operation: str) -> None:
    """Refuse an operation that would order around pending batched adds."""
    if space_name in _ACTIVE_BATCHES.get():
        msg = (
            f"{operation}() on {space_name} inside its own batch block "
            f"would silently order around the adds the block is holding; "
            f"leave the `with m.batch():` block first"
        )
        raise PettaError(
            msg
        )


class _Batch:
    """The write collector m.batch() answers; see its docstring for the
    stated edges (reads see the pre-batch space, remove and clear
    refuse, an exception discards).
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_pending", "_space", "_token")

    def __init__(self, space: MeTTa) -> None:
        self._space = space
        self._pending: list[Any] = []
        self._token: Any = None

    def __enter__(self) -> Self:
        current = _ACTIVE_BATCHES.get()
        name = self._space.name
        if name in current:
            msg = (
                f"a batch is already collecting for {name} in this "
                f"context; batches do not nest per space"
            )
            raise PettaError(
                msg
            )
        self._pending = []
        self._token = _ACTIVE_BATCHES.set(current | {name: self._pending})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ACTIVE_BATCHES.reset(self._token)
        pending, self._pending = self._pending, []
        if exc_type is None and pending:
            # The batch is no longer active here, so this is the one real
            # crossing, the engine's own bulk door underneath.
            self._space.add(*pending)

    def __len__(self) -> int:
        return len(self._pending)
