"""Purpose: the MeTTa runtime surface. One class binds a space name to the
process's engine and offers running source, loading files, structured space
edits, conjunctive queries with guards, bounds, scoped assumptions and
preparation, evaluation, Python-backed operations, proof-tree derivations
and a why-not diagnostic, all in PeTTa's own semantics.
Guarantees:
  - MeTTa.save preserves an existing target when validation, writing, or
    replacement fails [tested test_save_validation_preserves_existing_file,
    test_text_save_write_failure_preserves_existing_file,
    test_save_failure_preserves_existing_file]
  - MeTTa.save fsyncs a completed sibling file before replacing the target
    [tested test_save_syncs_before_replacing]
  - MeTTa.derivation distinguishes a finite-depth cutoff from no proof and
    accepts time and inference guards [tested
    test_depth_exhaustion_returns_a_partial_proof,
    test_unbounded_derivation_obeys_resource_guards]
  - an exhausted Cursor keeps raising StopIteration, while an explicitly
    closed Cursor refuses use [tested
    test_stream_agrees_with_query_and_closes_on_exhaustion,
    test_stream_pulls_rows_lazily_and_interleaves]
  - register_op and unregister_op are the paired operation lifecycle names
    [tested test_operation_registration_names_are_symmetric]
  - define accepts source-bearing Python functions and refuses callable
    objects before reading compiler metadata [tested
    test_define_refuses_callable_objects]
  - query, prepare, and stream preserve distinct variable columns in first
    appearance order [tested test_query_surfaces_share_column_order]
Owns:
  - MeTTa.save owns its sibling temporary file and removes it after every
    failed operation [tested test_save_failure_preserves_existing_file]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import builtins as _builtins
import os
import types
from collections.abc import Callable
from typing import Any, Literal, overload

from . import ops as _ops_module
from ._engine import Runtime, bridge, runtime, started
from ._space_definitions import clear_definitions, install_define, install_type
from ._space_diagnostics import derivations, explain_no_match
from ._space_execution import evaluate, profile_source, run_source, value_one
from ._space_persistence import (
    load_space,
    raise_unsafe_text_symbol,
    save_space,
)
from ._space_query import query_rows
from ._space_objects import (
    Cursor,
    EngineProfile,
    Prepared,
    _Assuming,
    _EngineFunction,
    _limits,
    _StatsBlock,
)
from .atoms import (
    Atom,
    Expr,
    Sym,
    Undefined,
    _to_atom,
    atom_from_wire,
    encode,
    parse,
)
from .derivation import Derivation
from .errors import EngineError
from .results import Rows

__all__ = ["Cursor", "EngineProfile", "MeTTa", "Prepared", "current_space"]


def current_space(default: str = "&self") -> str:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    if not started():
        return default
    row = bridge().query_once("current_metta_space(S)")
    return str(row["S"]) if row else default


def _to_stored_atom(value: Any) -> Expr:
    """Accept exactly the non-empty expression shape spaces can store."""
    atom = _to_atom(value)
    if not isinstance(atom, Expr) or not atom.children:
        detail = "the empty expression" if isinstance(atom, Expr) else atom.metatype
        raise TypeError(
            f"a stored atom is a non-empty expression; {atom!r} is {detail}. "
            f"Wrap a bare value in structure, as in (value {atom})."
        )
    return atom


class MeTTa:
    """A space bound to the engine: the way in from Python.

    PeTTa keeps one engine per process; every MeTTa instance shares it. The
    default space is &self, the space the CLI itself uses, so source pasted
    from a .metta file behaves identically here. Two MeTTa() calls therefore
    see the same &self state. Use fresh_space() when independent stored state
    is required. Named spaces isolate stored atoms; equations are process-wide,
    which is the engine's own rule.

        from petta import MeTTa, S, V

        m = MeTTa()
        m.run("(= (foo) boo) !(foo)")     # [[Sym('boo')]]
        m.add(S.Parent(S.Tom, S.Bob))
        m.query(S.Parent(V.x, S.Bob))     # Rows[x](Row(x=Sym('Tom')))
    """

    def __init__(
        self,
        space: str = "&self",
        *,
        verbose: bool = False,
        petta_path: str | None = None,
    ) -> None:
        if not space.startswith("&"):
            raise ValueError(
                f"a space name starts with &, as in &self or &kb; got {space!r}. "
                f"The prefix is load-bearing: is-space recognises it, and a $ "
                f"name would read back as a variable."
            )
        self._rt: Runtime = runtime(petta_path=petta_path, verbose=verbose)
        self._space = space
        self._ephemeral = False

    # ------------------------------------------------------------------ naming

    @property
    def space_name(self) -> str:
        return self._space

    def space(self, name: str) -> MeTTa:
        """Another space on the same engine."""
        return MeTTa(name)

    def fresh_space(self) -> MeTTa:
        """An anonymous space with a name nothing else is using.

        Works as a context manager: leaving the block drops the space, so a
        churn of short-lived spaces reuses names instead of growing the
        engine's module table.

            with m.fresh_space() as scratch:
                scratch.add(...)
        """
        row = self._rt.must("petta_py_new_space(Name)")
        fresh = MeTTa(row["Name"])
        fresh._ephemeral = True
        return fresh

    def drop(self) -> None:
        """Clear this space and release its name for reuse. Dropping a
        foreign space releases the binding and leaves the provider's own
        data alone; &self, the engine's own space, is cleared but its name
        never released. Subscriptions on the space cancel with it: a
        pooled name reused later must not deliver to the old life's
        watchers."""
        from .foreign import PROVIDERS, unregister_provider
        from .subscribe import _subscriptions_for

        for subscription in _subscriptions_for(self._space):
            subscription.cancel()
        if self._space in PROVIDERS:
            unregister_provider(self._rt, self._space)
        self.clear()
        if self._space != "&self":
            self._rt.must("petta_py_release_space(Space)", Space=self._space)

    def __enter__(self) -> MeTTa:
        if not self._ephemeral:
            raise TypeError(
                f"{self._space} was not created by fresh_space(); only an "
                f"anonymous space scopes to a with-block, since leaving the "
                f"block drops it. Call drop() deliberately for a named one."
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.drop()

    def __repr__(self) -> str:
        return f"MeTTa({self._space!r})"

    # ----------------------------------------------------------------- running

    @overload
    def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: Literal[False] = False,
        atomic: bool = False,
        speculative: bool = False,
    ) -> list[list[Atom]]: ...

    @overload
    def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: Literal[True],
        atomic: bool = False,
        speculative: bool = False,
    ) -> tuple[list[list[Atom]], str]: ...

    @overload
    def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool,
        atomic: bool = False,
        speculative: bool = False,
    ) -> list[list[Atom]] | tuple[list[list[Atom]], str]: ...

    def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool = False,
        atomic: bool = False,
        speculative: bool = False,
    ) -> list[list[Atom]] | tuple[list[list[Atom]], str]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.

        `using` names Python values the source refers to by bare symbol,
        the way DuckDB reads a local dataframe by its variable name:

            m.run("!(py-len graph)", using={"graph": my_graph})

        Each named symbol substitutes to its value (objects by identity),
        after reading, before anything runs.

        `timeout` (seconds) and `inferences` (engine steps) bound the call
        with the engine's own guards; passing either raises TimeLimitError
        or InferenceLimitError when the bound is hit, and whatever the
        source completed before the stop, writes included, stands. With
        `capture=True` the return value is (groups, text), text being
        everything the source printed, println! included.

        `atomic=True` runs the whole source inside the engine's own
        transaction/1: every write, facts and equations alike, commits
        whole, or rolls back whole when a directive throws; the inline
        (transaction ...) form does the same for a scope inside a
        program. `speculative=True` is the what-if twin through
        snapshot/1: the answers return and every write is discarded.
        Both cover engine state; a Python operation's side effects, and
        subscription callbacks already fired, stay where they happened.
        """
        return run_source(
            self._rt,
            self._space,
            source,
            using,
            timeout=timeout,
            inferences=inferences,
            capture=capture,
            atomic=atomic,
            speculative=speculative,
        )

    def profile(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[list[Atom]], EngineProfile]:
        """Run source under the engine's statistical profiler, answering
        (groups, profile): the groups exactly as run() answers them, and
        the profile carrying sample counters plus one row per predicate,
        self-ticks first.

            groups, prof = m.profile("!(big-computation)")
            prof.top(5)     # the five predicates the samples landed in

        The sampler is statistical: a program that finishes in
        milliseconds carries few samples, so profile something that runs.
        Profiling changes execution; it is a debugging surface, not a
        mode to leave on.
        """
        return profile_source(
            self._rt,
            self._space,
            source,
            using,
            timeout=timeout,
            inferences=inferences,
        )

    def save(self, path: str | os.PathLike[str], format: str = "metta") -> int:
        """Write every stored atom of this space, equations included, as
        MeTTa source by default, or as a version-pinned trusted cache with
        format="fast"; answers how many. A path ending .gz writes gzip
        compressed in either format, and load and import! read it back
        under the same name. The completed sibling file is synced and then
        atomically replaces the target, so a failed save leaves the old file
        intact. Atoms carrying live host objects cannot survive either file
        and are refused."""
        return save_space(self._rt, self._space, self.atoms(), path, format)

    def load(self, path: str | os.PathLike[str]) -> list[list[Atom]]:
        """Add a text program or trusted fast cache to this space.

        Existing atoms remain, so loading the same file twice adds two copies.
        Use clear() first or load into fresh_space() when replacement is wanted.
        A .gz path is detected and read through the decompressed bytes.
        """
        return load_space(self._rt, self._space, path)

    def parse(self, source: str) -> Atom:
        """Read one form into an atom without evaluating it."""
        return parse(source)

    # ------------------------------------------------------------- space edits

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. A stored atom is an
        expression, the engine's own storage shape, so anything else is
        refused here rather than failing silently inside."""
        wires = [_to_stored_atom(atom).to_wire() for atom in atoms]
        if not wires:
            return
        if len(wires) == 1:
            self._rt.do_must("petta_py_add", self._space, wires[0])
        else:
            self._rt.do_must("petta_py_add_many", self._space, wires)

    def add_table(self, head: Any, data: Any) -> int:
        """Any tabular source as facts (head v1 .. vn); answers how many.

            m.add_table("edge", polars_frame)         # or a pandas frame
            m.add_table("edge", {"src": [...], "dst": [...]})
            m.add_table("edge", [("a", "b"), ("b", "c")])

        The source is read by the interface it offers, never by library:
        iter_rows() (polars), itertuples() (pandas), a mapping of columns,
        or any iterable of row sequences. A mapping's fact positions are
        its own key order, and columns of unequal length are a hard error
        rather than a silent truncation. The reverse direction is
        rows.table(), the dict every DataFrame constructor takes."""
        import collections.abc as _abc

        head_atom = _to_atom(head)
        if hasattr(data, "iter_rows"):
            rows = data.iter_rows()
        elif hasattr(data, "itertuples"):
            rows = data.itertuples(index=False)
        elif isinstance(data, _abc.Mapping):
            rows = zip(*data.values(), strict=True)
        elif isinstance(data, _abc.Iterable):
            rows = iter(data)
        else:
            raise TypeError(
                f"add_table reads iter_rows(), itertuples(), a mapping of "
                f"columns, or an iterable of rows; "
                f"{type(data).__name__} offers none of those"
            )
        facts = [Expr([head_atom, *(encode(value) for value in row)]) for row in rows]
        self.add(*facts)
        return len(facts)

    def remove(self, atom: Any) -> bool:
        """Remove an atom, engine semantics: an equation removal reports
        whether it existed; a plain atom removal removes every copy and
        reports whether at least one copy existed."""
        removed = self._rt.apply_must(
            "petta_py_remove", self._space, _to_stored_atom(atom).to_wire()
        )
        result = atom_from_wire(removed)
        return bool(getattr(result, "value", True))

    def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        wires = self._rt.apply_must("petta_py_atoms", self._space)
        return [atom_from_wire(w) for w in wires]

    def count(self) -> int:
        row = self._rt.once("petta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    def cast(self, value, type_):
        """Answer value, narrowed to its Python-most spelling, when this
        space's type discipline admits it as type_: the same acceptance
        a typed call compiles, ':' declarations in this space and &self
        in scope, protocol types included. A refused cast raises
        petta.CastError naming the value's actual types, the loud
        spelling of what a typed call does silently."""
        from .casting import cast as _cast

        return _cast(self, value, type_)

    def trace(self, source: str, max_events: int = 1_000_000):
        """Run source under the engine's reduction trace and answer
        TraceEvent records: what entered reduction at which depth, what
        it answered, and which reductions failed (a call with no exit).
        The source executes for real, writes included, like run(); the
        wrap exists only while tracing, so untraced calls pay nothing.
        max_events bounds the recording, raising past it rather than
        accumulating a long run's trace without limit."""
        from .trace import trace as _trace

        return _trace(self, source, max_events=max_events)

    def lint(self):
        """Diagnose this space for the silently-wrong class: declared
        types nothing defines, arity mismatches, unbound body variables,
        duplicate equations, and references no function or fact carries.
        Answers petta.lint.Finding records, empty when nothing looks
        wrong."""
        from .lint import lint as _lint

        return _lint(self)

    def digest(self) -> str:
        """A sha256 hex digest of this space's content: every stored atom,
        equations included, canonicalized (variables numbered, multiset
        sorted) so the same atoms answer the same digest in any insertion
        order and in any process. Two spaces agree on digest() exactly
        when save() would write the same content. Live host objects have
        no cross-process identity and are refused, like save()."""
        from .foreign import require_capability

        require_capability(self._space, "enumerate", "digest")
        result = self._rt.apply_must("petta_py_digest", self._space)
        if not isinstance(result, list) or len(result) != 2:
            raise EngineError(f"petta_py_digest returned an invalid result: {result!r}")
        kind, value = result
        if kind == "object":
            atom = atom_from_wire(value)
            raise ValueError(
                f"{atom} carries a live Python object; it has no "
                f"cross-process identity to digest. Remove it, or digest "
                f"its data explicitly."
            )
        if kind == "symbol":
            raise_unsafe_text_symbol(atom_from_wire(value), "digest")
        if kind != "digest":
            raise EngineError(f"petta_py_digest returned an unknown result: {result!r}")
        return str(value)

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, atom: Any) -> bool:
        return self._rt.do("petta_py_contains", self._space, _to_atom(atom).to_wire())

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        clear_definitions(self)

    def __iadd__(self, atom: Any) -> MeTTa:
        self.add(atom)
        return self

    def __isub__(self, atom: Any) -> MeTTa:
        self.remove(atom)
        return self

    def __iter__(self):
        """Iterate the stored atoms: for atom in m."""
        return iter(self.atoms())

    # ----------------------------------------------------------------- queries

    def query(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Rows:
        """Match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order. `where` is a guard term over the same variables,
        evaluated per join and required true, so restrictions a pattern
        cannot spell (an inequality) compose onto the match:

            m.query(S.person(V.name, V.age), where=V.age >= 18)

        `limit` bounds the answers, the engine stopping at the count
        rather than trimming afterwards. `timeout` (seconds) and
        `inferences` (engine steps) bound the whole call, raising
        TimeLimitError or InferenceLimitError when hit, for joins whose
        size is not known in advance.

            m.query(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
        """
        return query_rows(
            self._rt,
            self._space,
            patterns,
            where=where,
            limit=limit,
            timeout=timeout,
            inferences=inferences,
        )

    def stream(
        self,
        *patterns: Any,
        where: Any | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Cursor:
        """query(), pulled: the same conjunction and guard, answered one
        row at a time through a cursor the engine holds open.

            with m.stream(S.edge(V.a, V.b), S.edge(V.b, V.c)) as rows:
                for row in rows:
                    if wanted(row):
                        break            # nothing further is even joined

        The join's state lives inside an SWI engine between pulls, each
        pull is one ordinary call, and unrelated calls interleave freely,
        so a huge join costs one row of work per row actually taken where
        query() computes and decodes every answer up front. `timeout`
        bounds each pull's wall time; `inferences` is one budget for the
        cursor's whole engine work, spent across pulls, because an
        engine's inferences are its own. The cursor enumerates under the
        engine's logical update view: writes made after the first pull
        are not seen by this cursor.
        """
        return Cursor(self, patterns, where, timeout, inferences)

    def assuming(self, *facts: Any) -> _Assuming:
        """Facts held only inside a with-block: the assumptions reading of
        a what-if query, added on entry, removed on exit, exceptions
        included.

            with m.assuming(S.closed(S.bridge)):
                detour = m.query(S.route(V.r), where=...)
        """
        return _Assuming(self, [_to_atom(f) for f in facts])

    def prepare(self, *patterns: Any, where: Any | None = None) -> Prepared:
        """A query whose shape is fixed and whose facts are not: the wire
        form and columns build once, and each solve() may bring per-call
        facts (given=) that leave nothing behind.

            route = m.prepare(S.path(V.a, V.b), where=V.a != ...)
            route.solve()
            route.solve(given=[S.edge(S.x, S.y)])
        """
        return Prepared(
            self, [_to_atom(p) for p in patterns], None if where is None else _to_atom(where)
        )

    # -------------------------------------------------------------- evaluation

    @overload
    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: Literal[False] = False,
        residuals: bool = False,
    ) -> list[Atom | Undefined]: ...

    @overload
    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: Literal[True],
        residuals: bool = False,
    ) -> tuple[list[Atom | Undefined], str]: ...

    @overload
    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool,
        residuals: bool = False,
    ) -> list[Atom | Undefined] | tuple[list[Atom | Undefined], str]: ...

    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool = False,
        residuals: bool = False,
    ) -> list[Atom | Undefined] | tuple[list[Atom | Undefined], str]:
        """Evaluate a term, returning every answer.

        This is what !(...) runs, minus the printing: the engine's
        translate_expr over the term, then its goals. Nondeterminism means
        the list can hold any number of answers, including none.

        Every answer carries its truth: an answer that is undefined under
        Well Founded Semantics (a tabled loop through tnot, reachable via
        translatePredicate or injected Prolog) arrives as an Undefined
        holding the answer and the delay condition that makes it
        undefined, never as an ordinary-looking value. `residuals=True`
        additionally fills each Undefined's .residual with the residual
        program, the clauses of the loop itself. run() does not carry the
        third truth value; evaluate through eval() when it matters.

        `timeout` (seconds) and `inferences` (engine steps) bound the call,
        raising TimeLimitError or InferenceLimitError when hit. With
        `capture=True` the return value is (answers, text), text being
        everything the evaluation printed.
        """
        return evaluate(
            self._rt,
            self._space,
            target,
            timeout,
            inferences,
            capture=capture,
            residuals=residuals,
        )

    def value(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """THE answer of evaluating target, as a plain Python value.

            m.value("(+ 1 2)")            # 3
            m.value(S.fact(5))            # 120

        Exactly one answer is the contract: none or several raise naming
        the count, because a caller asking for the value has asserted
        there is one. Grounded answers unwrap to their Python values;
        symbols and structure stay atoms. eval() is the spelling for any
        number of answers, and carries the same timeout/inferences bounds."""
        answers = self.eval(target, timeout=timeout, inferences=inferences)
        return value_one(target, answers)

    def stats(self) -> _StatsBlock:
        """The engine's own counters over a with-block, as deltas.

            with m.stats() as s:
                m.query(S.edge(V.x, V.y), S.edge(V.y, V.z))
            s.inferences        # engine steps the block spent
            s.cputime           # engine CPU seconds
            s.walltime          # wall seconds, Python's clock
            s.gc_count, s.gc_freed, s.gc_time
            s.table_bytes       # answer-table bytes grown, tabling's memory

        The counters are the engine's statistics/2, and the engine is one
        per process, so a block that runs other threads' engine work counts
        that work too; the honest reading is "what the engine did while
        this block ran". The z3py Solver.statistics() reading, on the
        engine this library actually has."""
        return _StatsBlock(self._rt)

    # -------------------------------------------------------------- operations

    def register_op(
        self,
        fn: Callable | None = None,
        *,
        name: str | None = None,
        typed: bool = True,
        raw: bool = False,
        pass_atoms: bool = False,
        arities: list[int] | None = None,
    ):
        """Register a Python callable as a MeTTa function, decorator-style.

            @m.register_op
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.register_op
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        Annotations become a (: ...) declaration unless typed=False. A raw
        operation skips the wire encoding both ways, which suits tensor and
        number work; symbols reach it as plain strings, so keep raw off when
        the symbol-string distinction matters. pass_atoms hands the callable
        Atom objects instead of decoded Python values. unregister_op(name)
        removes every registered arity.
        """

        def apply(f: Callable) -> Callable:
            return _ops_module.register(
                self._rt,
                f,
                name=name,
                typed=typed,
                raw=raw,
                pass_atoms=pass_atoms,
                space=self._space,
                arities=arities,
            )

        return apply(fn) if fn is not None else apply

    def unregister_op(self, name: str) -> None:
        """Remove a registered operation, every arity of it."""
        _ops_module.unregister(self._rt, name)

    # The paired names are canonical. These spellings keep existing
    # decorators and notebooks executable while callers migrate together.
    op = register_op
    unregister = unregister_op

    # -------------------------------------------------------------- inspection

    def builtins(self) -> list[str]:
        """Every function name the engine has registered."""
        return self._rt.builtins()

    def is_function(self, name: str) -> bool:
        return bool(self._rt.once("petta_py_is_function(Name)", Name=name))

    def is_function_here(self, name: str) -> bool:
        """Whether a function would answer from THIS space: it has clauses
        this space's module sees, its own or the shared ones in user.
        Another space's equations are invisible here and do not count."""
        return bool(
            self._rt.once("petta_py_function_visible(Space, Name)", Space=self._space, Name=name)
        )

    def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        row = self._rt.once("petta_py_arities(Name, As)", Name=name)
        return list(row.get("As", []))

    # ----------------------------------------------------------- subscriptions

    def subscribe(
        self,
        pattern: Any,
        callback: Callable | None = None,
        *,
        on: str = "add",
    ):
        """A standing query on this space: every added (or removed, or
        both) atom unifying with the pattern becomes an Event.

            seen = []
            sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))
            m.add(S.order(1))          # seen[0].bindings["id"] == 1
            sub.cancel()

        With a callback, delivery is synchronous, inside the write that
        caused it (the callback may write back; the engine re-enters
        cleanly; an infinite add-triggers-add loop is the author's own).
        Without one, events queue on the subscription and drain() empties
        them: the mailbox reading. Removal events for plain atoms may fire
        for atoms that were never stored, since the engine's removal is
        retractall; re-check the space rather than trust the event.
        """
        from .subscribe import subscribe as _subscribe

        return _subscribe(self._rt, self._space, _to_atom(pattern), callback, on)

    def prolog(self) -> None:
        """Drop into the engine's own interactive Prolog toplevel, the
        deepest debugging lever there is: listing/1 shows compiled
        equations, trace/0 steps through them, and quitting the toplevel
        returns here with the session intact. janus's own janus.prolog(),
        surfaced where the debugging happens."""
        self._rt._janus.prolog()

    # ------------------------------------------------------------- diagnostics

    def derivation(
        self,
        target: Any,
        depth: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[Derivation]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path. The default walks each proof
        without a depth cutoff. A positive depth returns a partial tree with
        Truncated nodes when its budget ends, so an empty list means no proof.
        `timeout` and `inferences` guard the whole search. An evaluation error
        inside a proof surfaces as itself rather than as an empty proof list.
        """
        return derivations(
            self._rt,
            self._space,
            target,
            depth,
            timeout=timeout,
            inferences=inferences,
        )

    def why(self, pattern: Any) -> str:
        """Why a pattern matches nothing here, in words.

        Checks the cheap explanations in order: unknown function, wrong
        arity, no stored atoms with that head. Honest when it cannot tell.
        """
        return explain_no_match(self, pattern)

    # ------------------------------------------------------------ definitions

    def define(self, fn: types.FunctionType):
        """Compile a Python function into MeTTa equations, decorator-style.

        Written for whoever is fluent in Python rather than s-expressions:
        the body is read as syntax and lowered deterministically, refusals
        name the construct, the line and what to write instead, and the
        original stays reachable as .py, a twin the equations can be checked
        against on any ground input.

            @m.define
            def add_one(n):
                return n + 1

            m.run("!(add-one 5)")       # [[6]]
            add_one.py(5)               # 6, ordinary Python

        The equation name follows the operation naming rule: underscores
        in the Python name become hyphens in MeTTa.

        A generator compiles to nondeterminism (each yield one answer), a
        lambda to the engine's own |->, a comprehension to map-atom and
        filter-atom, and match(Pattern(x, y), template) to a match against
        the running space, lowercase free names in the pattern binding as
        variables.
        """
        return install_define(self, fn)

    def type(
        self,
        cls: _builtins.type | None = None,
        *,
        accessors: bool = True,
        methods: bool = True,
    ):
        """Declare a Python class INTO this space, decorator-style: the
        (: ...) declarations land as atoms, an expression-image class
        (a dataclass, a NamedTuple) gains one accessor equation per
        field, and its own METHODS register as MeTTa functions, so the
        class crosses with its behavior, not only its structure.

            @m.type
            @dataclass
            class Point:
                x: float
                y: float
                def norm(self) -> float:
                    return (self.x ** 2 + self.y ** 2) ** 0.5

            m.run("!(Point-x (Point 3.0 4.0))")        # [[3.0]]
            m.run("!(Point-norm (Point 3.0 4.0))")     # [[5.0]]

        A method receives the instance whether it arrives as a
        constructor TERM (rebuilt through the translator) or as a live
        handle, and a result the translator knows projects back as a
        term, so a method answering the class answers something MeTTa
        keeps matching and Python builds back. An equation over the
        constructor is then a method written in MeTTa itself, on equal
        footing. An Enum declares its members; get-type sees them all.
        Returns the class, so it stacks under @dataclass.
        """
        return install_type(self, cls, accessors=accessors, methods=methods)

    def fn(self, name: str) -> _EngineFunction:
        """Any engine function as an ordinary Python callable.

            car = m.fn("car-atom")
            car(m.parse("(1 2 3)"))     # 1
            m.fn("superpose").all(expr(1, 2, 3))   # [1, 2, 3]

        Calling expects exactly one answer and raises otherwise, the loud
        reading; .all returns every answer, nondeterminism included.
        """
        return _EngineFunction(self, name)

    # ---------------------------------------------------------- integrations

    def integrate(self, target: Any) -> str:
        """Install a library integration; see petta.integrate."""
        from . import integrate as _integrate

        return _integrate.integrate(self, target)

    def register_space(self, name: str, provider: Any) -> Any:
        """A space answered by Python: matches, adds and removals route to
        the provider, so a table, a dataframe or a service is matchable the
        way stored atoms are. See petta.foreign.SpaceProvider."""
        from .foreign import register_provider

        register_provider(self._rt, name, provider)
        return provider

    def unregister_space(self, name: str) -> None:
        from .foreign import unregister_provider

        unregister_provider(self._rt, name)

    # ------------------------------------------------------------ interop

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt
