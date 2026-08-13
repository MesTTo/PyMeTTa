"""Purpose: the MeTTa runtime surface. One class binds a space name to the
process's engine and offers running source, loading files, structured space
edits, conjunctive queries with guards, bounds, scoped assumptions and
preparation, evaluation, Python-backed operations, proof-tree derivations
and a why-not diagnostic, all in PeTTa's own semantics.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import weakref
from typing import Any, Callable, Iterable

from . import ops as _ops_module
from ._engine import Runtime, runtime
from .atoms import Atom, Expr, Sym, Var, alpha_eq, encode, from_wire, parse, variables
from .derivation import Derivation
from .errors import EngineError, PettaError
from .results import Rows, _row_class

__all__ = ["MeTTa", "Prepared", "Cursor", "EngineProfile", "current_space"]


def current_space(default: str = "&self") -> str:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    import petta as pkg

    if pkg.janus is None:
        return default
    row = pkg.janus.query_once("current_metta_space(S)")
    return str(row["S"]) if row else default

# @define bookkeeping is keyed (space name, function name) process-wide,
# because equations live in spaces, not in MeTTa instances: two instances
# bound to one space stack clauses of one function together.
_DEFINE_CLAUSES: dict[tuple[str, str], list[dict]] = {}
_DECLARED_DEFINES: dict[tuple[str, str], bool] = {}
_DEFINED_GENERATORS: set[tuple[str, str]] = set()


def _to_atom(value: Any) -> Atom:
    """Accept an Atom, MeTTa source text, or an encodable Python value."""
    if isinstance(value, Atom):
        return value
    if isinstance(value, str):
        return parse(value)
    return encode(value)


def _open_maybe_gz(path: str, mode: str):
    """Open a save or load path, gzip-compressed when it ends .gz. The
    engine side mirrors this with zlib's gzopen, so both readers accept
    either writer's files."""
    if path.endswith(".gz"):
        import gzip

        return gzip.open(path, mode)
    return open(path, mode)


def _limits(timeout: float | None, inferences: int | None) -> tuple[float, int] | None:
    """Validate the per-call bounds into the shim's (-1 = none) pair."""
    if timeout is None and inferences is None:
        return None
    if timeout is not None and not timeout > 0:
        raise ValueError(f"timeout must be positive seconds, got {timeout!r}")
    if inferences is not None and not inferences > 0:
        raise ValueError(f"inferences must be a positive count, got {inferences!r}")
    return (
        -1.0 if timeout is None else float(timeout),
        -1 if inferences is None else int(inferences),
    )


class MeTTa:
    """A space bound to the engine: the way in from Python.

    PeTTa keeps one engine per process; every MeTTa instance shares it. The
    default space is &self, the space the CLI itself uses, so source pasted
    from a .metta file behaves identically here. Named spaces isolate stored
    atoms; equations are process-wide, which is the engine's own rule.

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

    def space(self, name: str) -> "MeTTa":
        """Another space on the same engine."""
        return MeTTa(name)

    def fresh_space(self) -> "MeTTa":
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
        from .subscribe import _SUBSCRIPTIONS

        for subscription in [
            s for s in _SUBSCRIPTIONS if s.space == self._space
        ]:
            subscription.cancel()
        if self._space in PROVIDERS:
            unregister_provider(self._rt, self._space)
        self.clear()
        if self._space != "&self":
            self._rt.must("petta_py_release_space(Space)", Space=self._space)

    def __enter__(self) -> "MeTTa":
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

    def _run_target(self, source: str, using: dict[str, Any] | None) -> tuple[str, list]:
        """The (entry point, inputs) pair a run of this source crosses as."""
        if not using:
            return "petta_py_run", [source, self._space]
        pairs = [[name, encode(value).to_wire()] for name, value in using.items()]
        return "petta_py_run_using", [source, self._space, pairs]

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
        if atomic and speculative:
            raise ValueError(
                "atomic= and speculative= are exclusive: one commits the "
                "run's writes whole, the other discards them whole"
            )
        pred, ins = self._run_target(source, using)
        limits = _limits(timeout, inferences)
        if limits is None and not (capture or atomic or speculative):
            names = ["Src", "Space"] if not using else ["Src", "Space", "Pairs"]
            goal = f"{pred}({', '.join(names)}, Groups)"
            row = self._rt.must(goal, **dict(zip(names, ins)))
            out = row.get("Groups", [])
        else:
            if atomic:
                pred, ins = "petta_py_atomic", [pred, ins]
            elif speculative:
                pred, ins = "petta_py_speculative", [pred, ins]
            if capture:
                pred, ins = "petta_py_captured", [pred, ins]
            seconds, steps = limits if limits is not None else (-1.0, -1)
            row = self._rt.must(
                "petta_py_limited(T, I, P, Ins, Out)",
                T=seconds, I=steps, P=pred, Ins=ins,
            )
            out = row.get("Out", [])
        if capture:
            groups_wire, text = out
            groups = [[from_wire(w) for w in group] for group in groups_wire]
            return groups, text
        return [[from_wire(w) for w in group] for group in out]

    def profile(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[list[Atom]], "EngineProfile"]:
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
        pred, ins = self._run_target(source, using)
        seconds, steps = _limits(timeout, inferences) or (-1.0, -1)
        row = self._rt.must(
            "petta_py_limited(T, I, P, Ins, Out)",
            T=seconds, I=steps, P="petta_py_profiled", Ins=[pred, ins],
        )
        out, samples, ticks, nodes = row["Out"]
        groups = [[from_wire(w) for w in group] for group in out]
        return groups, EngineProfile(samples, ticks, nodes)

    def save(self, path: str, format: str = "metta") -> int:
        """Write every stored atom of this space, equations included, as
        MeTTa source by default, or as a version-pinned trusted cache with
        format="fast"; answers how many. A path ending .gz writes gzip
        compressed in either format, and load and import! read it back
        under the same name. Atoms carrying live host objects cannot
        survive either file and are refused."""
        if format not in ("metta", "fast"):
            raise ValueError(
                f"save format must be 'metta' or 'fast', got {format!r}"
            )
        if format == "fast":
            result = self._rt.apply_must(
                "petta_py_fast_save", str(path), self._space
            )
            if not isinstance(result, list) or len(result) != 2:
                raise EngineError(
                    f"petta_py_fast_save returned an invalid result: {result!r}"
                )
            kind, value = result
            if kind == "object":
                atom = from_wire(value)
                raise ValueError(
                    f"{atom} carries a live Python object; a file cannot "
                    f"hold it. Remove it, or persist its data explicitly."
                )
            if kind != "saved":
                raise EngineError(
                    f"petta_py_fast_save returned an unknown result: {result!r}"
                )
            return int(value)
        atoms = self.atoms()
        lines = []
        for atom in atoms:
            if not _serializable(atom):
                raise ValueError(
                    f"{atom} carries a live Python object; a file cannot "
                    f"hold it. Remove it, or persist its data explicitly."
                )
            lines.append(str(atom))
        with _open_maybe_gz(str(path), "wt") as handle:
            handle.write("\n".join(lines) + ("\n" if lines else ""))
        return len(atoms)

    def load(self, path: str) -> list[list[Atom]]:
        """Load a text program or an auto-detected trusted fast cache,
        gzip-compressed or plain; a .gz path sniffs and reads through
        the decompressed bytes."""
        file = str(path)
        try:
            with _open_maybe_gz(file, "rb") as handle:
                is_fast = handle.read(len(b"PETTA-CACHE\t")) == b"PETTA-CACHE\t"
        except OSError:
            is_fast = False
        if is_fast:
            return self._load_fast(file)
        row = self._rt.must(
            "petta_py_load(File, Space, Groups)", File=file, Space=self._space
        )
        return [[from_wire(w) for w in group] for group in row.get("Groups", [])]

    def _load_fast(self, path: str) -> list[list[Atom]]:
        """Validate a trusted cache header, then let the engine read it."""
        import re

        expected_text = self._rt.apply_must("petta_py_fast_header")
        expected_fields = str(expected_text).encode("ascii").split(b"\t")
        try:
            with _open_maybe_gz(path, "rb") as handle:
                actual = handle.readline(512)
        except OSError as exc:
            raise EngineError(
                f"cannot read the fast cache header from {path!r}: {exc}; "
                f"re-save the cache from its source data"
            ) from exc

        def reject(reason: str) -> EngineError:
            return EngineError(
                f"cannot load fast cache {path!r}: {reason}; re-save it with "
                f"this PeTTa and SWI-Prolog version"
            )

        if not actual.endswith(b"\n"):
            raise reject("the header is truncated or malformed")
        fields = actual[:-1].split(b"\t")
        if len(fields) != 5:
            raise reject("the header is malformed")
        if fields[0] != expected_fields[0]:
            raise reject("the cache marker is invalid")
        if fields[1] != expected_fields[1]:
            raise reject(
                f"magic tag {fields[1]!r} does not match {expected_fields[1]!r}"
            )
        if fields[2] != expected_fields[2]:
            raise reject(
                f"format version {fields[2]!r} does not match "
                f"{expected_fields[2]!r}"
            )
        if fields[3] != expected_fields[3]:
            raise reject(
                f"SWI-Prolog version {fields[3]!r} does not match the running "
                f"version {expected_fields[3]!r}"
            )
        if not re.fullmatch(rb"[0-9a-f]{64}", fields[4]):
            raise reject("the integrity hash is malformed")
        try:
            self._rt.do_must("petta_py_fast_load", path, self._space)
        except EngineError as exc:
            message = str(exc)
            if not any(
                tag in message
                for tag in (
                    "petta_fast_header_mismatch",
                    "petta_fast_integrity_header",
                    "petta_fast_integrity_mismatch",
                    "petta_fast_read_failed",
                    "petta_fast_payload_not_atom_list",
                )
            ):
                raise EngineError(
                    f"fast load failed while adding atoms from {path!r}: {exc}"
                ) from exc
            raise EngineError(
                f"fast load failed for {path!r}: {exc}. The cache is corrupt "
                f"or incomplete; re-save it from the source data."
            ) from exc
        return []

    def parse(self, source: str) -> Atom:
        """Read one form into an atom without evaluating it."""
        return parse(source)

    # ------------------------------------------------------------- space edits

    def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. A stored atom is an
        expression, the engine's own storage shape, so anything else is
        refused here rather than failing silently inside."""
        wires = []
        for a in atoms:
            atom = _to_atom(a)
            if not isinstance(atom, Expr):
                raise TypeError(
                    f"a stored atom is an expression; {atom!r} is "
                    f"{atom.metatype}. Wrap a bare value in structure, as in "
                    f"(value {atom})."
                )
            wires.append(atom.to_wire())
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
        facts = [
            Expr([head_atom, *(encode(value) for value in row)]) for row in rows
        ]
        self.add(*facts)
        return len(facts)

    def remove(self, atom: Any) -> bool:
        """Remove an atom, engine semantics: an equation removal reports
        whether it existed; a plain atom removal removes every copy."""
        removed = self._rt.apply_must(
            "petta_py_remove", self._space, _to_atom(atom).to_wire()
        )
        result = from_wire(removed)
        return bool(getattr(result, "value", True))

    def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        wires = self._rt.apply_must("petta_py_atoms", self._space)
        return [from_wire(w) for w in wires]

    def count(self) -> int:
        row = self._rt.once("petta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    def digest(self) -> str:
        """A sha256 hex digest of this space's content: every stored atom,
        equations included, canonicalized (variables numbered, multiset
        sorted) so the same atoms answer the same digest in any insertion
        order and in any process. Two spaces agree on digest() exactly
        when save() would write the same content. Live host objects have
        no cross-process identity and are refused, like save()."""
        result = self._rt.apply_must("petta_py_digest", self._space)
        if not isinstance(result, list) or len(result) != 2:
            raise EngineError(
                f"petta_py_digest returned an invalid result: {result!r}"
            )
        kind, value = result
        if kind == "object":
            atom = from_wire(value)
            raise ValueError(
                f"{atom} carries a live Python object; it has no "
                f"cross-process identity to digest. Remove it, or digest "
                f"its data explicitly."
            )
        if kind != "digest":
            raise EngineError(
                f"petta_py_digest returned an unknown result: {result!r}"
            )
        return str(value)

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, atom: Any) -> bool:
        return self._rt.do(
            "petta_py_contains", self._space, _to_atom(atom).to_wire()
        )

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        self._rt.must("petta_py_clear(Space)", Space=self._space)
        # The @define bookkeeping follows the equations it describes.
        for registry in (_DEFINE_CLAUSES, _DECLARED_DEFINES):
            for key in [k for k in registry if k[0] == self._space]:
                del registry[key]
        for key in [k for k in _DEFINED_GENERATORS if k[0] == self._space]:
            _DEFINED_GENERATORS.discard(key)
        # Reflection facts describing this space follow it too, so a pooled
        # name reused later does not inherit another life's story. One
        # engine crossing removes them all; per-fact crossings measured
        # 64ms for 10,000 defines.
        from .ops import REFLECTION_SPACE

        if self._space != REFLECTION_SPACE:
            self._rt.must(
                "petta_py_reflect_clear_defined(Space)", Space=self._space
            )

    def __iadd__(self, atom: Any) -> "MeTTa":
        self.add(atom)
        return self

    def __isub__(self, atom: Any) -> "MeTTa":
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
        if limit is not None and limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        atoms = [_to_atom(p) for p in patterns]
        columns: list[str] = []
        for a in atoms:
            for name in variables(a):
                # `_` is anonymous: fresh at every occurrence, never a column.
                if name != "_" and name not in columns:
                    columns.append(name)
        wires = [a.to_wire() for a in atoms]
        if where is not None:
            pred = "petta_py_query_guarded_all"
            ins = [self._space, wires, _to_atom(where).to_wire(), columns, limit or 0]
        elif limit is not None:
            pred, ins = "petta_py_query_limit_all", [self._space, wires, columns, limit]
        else:
            pred, ins = "petta_py_query_all", [self._space, wires, columns]
        limits = _limits(timeout, inferences)
        if limits is None:
            answered = self._rt.apply_must(pred, *ins)
        else:
            answered = self._rt.apply_must("petta_py_limited", *limits, pred, ins)
        decoded = [tuple(from_wire(v) for v in r) for r in answered]
        return Rows(tuple(columns), decoded)

    def stream(
        self,
        *patterns: Any,
        where: Any | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> "Cursor":
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

    def assuming(self, *facts: Any) -> "_Assuming":
        """Facts held only inside a with-block: the assumptions reading of
        a what-if query, added on entry, removed on exit, exceptions
        included.

            with m.assuming(S.closed(S.bridge)):
                detour = m.query(S.route(V.r), where=...)
        """
        return _Assuming(self, [_to_atom(f) for f in facts])

    def prepare(self, *patterns: Any, where: Any | None = None) -> "Prepared":
        """A query whose shape is fixed and whose facts are not: the wire
        form and columns build once, and each solve() may bring per-call
        facts (given=) that leave nothing behind.

            route = m.prepare(S.path(V.a, V.b), where=V.a != ...)
            route.solve()
            route.solve(given=[S.edge(S.x, S.y)])
        """
        return Prepared(self, [_to_atom(p) for p in patterns],
                        None if where is None else _to_atom(where))

    # -------------------------------------------------------------- evaluation

    def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool = False,
        residuals: bool = False,
    ) -> list[Atom] | tuple[list[Atom], str]:
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
        entry = "petta_py_eval_res_all" if residuals else "petta_py_eval_all"
        pred, ins = entry, [self._space, _to_atom(target).to_wire()]
        limits = _limits(timeout, inferences)
        if limits is None and not capture:
            wires = self._rt.apply_must(pred, *ins)
        else:
            if capture:
                pred, ins = "petta_py_captured", [pred, ins]
            seconds, steps = limits if limits is not None else (-1.0, -1)
            out = self._rt.apply_must("petta_py_limited", seconds, steps, pred, ins)
            if capture:
                wires, text = out
                return [from_wire(w) for w in wires], text
            wires = out
        return [from_wire(w) for w in wires]

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
        if len(answers) != 1:
            raise EngineError(
                f"value({_to_atom(target)}) expected exactly one answer, "
                f"got {len(answers)}; use eval() for any number"
            )
        answer = answers[0]
        from .atoms import Gnd, Undefined, decode

        if isinstance(answer, Undefined):
            raise EngineError(
                f"value({_to_atom(target)}) answered with undefined truth "
                f"({answer.why}); a caller asking for THE value has "
                f"asserted a definite one exists. eval() carries the "
                f"third truth value."
            )
        return decode(answer) if isinstance(answer, Gnd) else answer

    def stats(self) -> "_StatsBlock":
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

    def op(
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

            @m.op
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.op
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        Annotations become a (: ...) declaration unless typed=False. A raw
        operation skips the wire encoding both ways, which suits tensor and
        number work; symbols reach it as plain strings, so keep raw off when
        the symbol-string distinction matters. pass_atoms hands the callable
        Atom objects instead of decoded Python values.
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

    def unregister(self, name: str) -> None:
        """Remove a registered operation, every arity of it."""
        _ops_module.unregister(self._rt, name)

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
            self._rt.once(
                "petta_py_function_visible(Space, Name)", Space=self._space, Name=name
            )
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

    def derivation(self, target: Any, depth: int = 30) -> list[Derivation]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path. Depth bounds the SEARCH, and
        an evaluation error inside a proof surfaces as itself rather than
        as an empty proof list.
        """
        if depth <= 0:
            raise ValueError(
                f"derivation depth must be positive, got {depth}: a zero "
                f"budget would answer no proofs for everything"
            )
        rows = self._rt.iter(
            "petta_py_derivation(Space, W, D, T)",
            Space=self._space,
            W=_to_atom(target).to_wire(),
            D=depth,
        )
        return [Derivation.from_atom(from_wire(r["T"])) for r in rows]

    def why(self, pattern: Any) -> str:
        """Why a pattern matches nothing here, in words.

        Checks the cheap explanations in order: unknown function, wrong
        arity, no stored atoms with that head. Honest when it cannot tell.
        """
        atom = _to_atom(pattern)
        if not isinstance(atom, Expr) or not atom.children:
            return f"{atom} is not an expression pattern"
        head = atom.head
        if not isinstance(head, Sym):
            return f"the pattern head {head} is not a symbol"
        name = head.name
        stored = [
            a
            for a in self.atoms()
            if isinstance(a, Expr) and isinstance(a.head, Sym) and a.head.name == name
        ]
        if stored:
            sizes = sorted({len(a) for a in stored})
            if len(atom) not in sizes:
                return (
                    f"{name} atoms here have {sizes} elements; the pattern has "
                    f"{len(atom)}"
                )
            return (
                f"{len(stored)} {name} atom(s) exist here but none unifies with "
                f"{atom}"
            )
        if self.is_function(name):
            return (
                f"no {name} atoms are stored here; {name} is a function, so its "
                f"answers come from evaluation, not matching: try eval"
            )
        return f"nothing here is headed by {name}, and no function has that name"

    # ------------------------------------------------------------ definitions

    def define(self, fn: Callable):
        """Compile a Python function into MeTTa equations, decorator-style.

        Written for whoever is fluent in Python rather than s-expressions:
        the body is read as syntax and lowered deterministically, refusals
        name the construct, the line and what to write instead, and the
        original stays reachable as .py, a twin the equations can be checked
        against on any ground input.

            @m.define
            def fact(n):
                if n == 0:
                    return 1
                return n * fact(n - 1)

            m.run("!(fact 5)")          # [[120]]
            fact.py(5)                  # 120, ordinary Python

        A generator compiles to nondeterminism (each yield one answer), a
        lambda to the engine's own |->, a comprehension to map-atom and
        filter-atom, and match(Pattern(x, y), template) to a match against
        the running space, lowercase free names in the pattern binding as
        variables.
        """
        from ._ops import REGISTRY
        from .define import (
            Defined,
            canonical_aux,
            compile_function,
            hazard_twin,
            twin_dispatcher,
        )
        from .errors import CompileError
        from .ops import (
            class_declarations,
            declaration_exprs,
            referenced_classes,
            resolved_annotations,
        )

        def nondet(called: str) -> bool:
            for spelling in (called, called.replace("_", "-")):
                operation = REGISTRY.get(spelling)
                if operation is not None and operation.kind in ("many", "raw_many"):
                    return True
                if (self._space, spelling) in _DEFINED_GENERATORS:
                    return True
            return False

        # The equation's name follows the operation rule: underscores read
        # as hyphens, one policy across both decorators.
        name = fn.__name__.replace("_", "-")
        compiled = compile_function(
            fn, known=self.is_function, nondet=nondet, metta_name=name
        )
        params, patterns, body = compiled.params, compiled.patterns, compiled.body
        # Clause stacking is per (space, name), process-wide: equations live
        # in the space, not in whichever MeTTa instance happened to add them.
        earlier = _DEFINE_CLAUSES.setdefault((self._space, name), [])
        first_clause = not earlier
        if not earlier and self.is_function_here(name):
            raise CompileError(
                f"{name!r} is already a function this space answers (an "
                f"engine builtin, an operation, or an equation): defining it "
                f"would stack a clause onto it and the existing definition "
                f"would keep answering first. Pick another name, or add the "
                f"equation deliberately with m.run.",
                construct="name collision",
            )
        if patterns and any(not clause["patterns"] for clause in earlier):
            raise CompileError(
                f"a clause of {name} with a literal head comes after the "
                f"general clause, which already matches everything; define "
                f"the general clause last",
                construct="clause order",
            )
        # MeTTa equations are alternatives, and a Python author stacking
        # clauses means first-match, so each clause is guarded against every
        # earlier literal head it would otherwise also answer for. The guard
        # is ordinary MeTTa, visible in .source(), never a hidden rule.
        body = _guard_against(
            body, [clause["patterns"] for clause in earlier], patterns, params
        )
        head = Expr(
            [Sym(name), *(patterns.get(p, Var(p)) for p in params)]
        )
        equation = Expr([Sym("="), head, body])
        dispatcher = twin_dispatcher(fn)
        # Idempotence compares with auxiliary helper names canonicalized:
        # every compilation serials its helpers, so the same source re-run
        # must be recognized through the renaming.
        canonical = canonical_aux(equation, name)
        clause_twin = (
            hazard_twin(name, compiled.hazards) if compiled.hazards else compiled.twin
        )
        replaced = None
        for position, clause in enumerate(earlier):
            if alpha_eq(canonical_aux(clause["equation"], name), canonical):
                # The identical clause again, a re-run cell or module
                # reload: adding it would duplicate answers, so it stands.
                return Defined(
                    name, params, body, dispatcher, self,
                    patterns=patterns, runtime_ops=compiled.runtime_ops,
                )
            if clause["patterns"] == patterns:
                replaced = position
        if replaced is not None:
            # The same head with a new body is a redefinition of that
            # clause, the notebook reading; the old equation goes, the new
            # one takes its place in both the space and the twin dispatch.
            self.remove(earlier[replaced]["equation"])
            earlier[replaced] = {"patterns": dict(patterns), "equation": equation}
            dispatcher.clauses[replaced] = clause_twin
        else:
            earlier.append({"patterns": dict(patterns), "equation": equation})
            dispatcher.clauses.append(clause_twin)
        for helper_equation in compiled.aux:
            self.add(helper_equation)
        self.add(equation)
        if first_clause:
            # The function reflects into the library's own space, one fact
            # per (space, name), following the space through clear().
            self._rt.must(
                "petta_py_add(Space, W)",
                Space=_ops_module.REFLECTION_SPACE,
                W=Expr([Sym("defined"), Sym(self._space), Sym(name)]).to_wire(),
            )
        # Annotations declare the type, exactly as they do for operations,
        # once per name so stacked clauses do not repeat the declaration.
        annotated = resolved_annotations(fn)
        if any(k != "return" for k in annotated) and not _DECLARED_DEFINES.get(
            (self._space, name)
        ):
            import inspect as _inspect

            annotations = [
                annotated.get(p, _inspect.Parameter.empty) for p in params
            ]
            ret_annotation = annotated.get("return", _inspect.Parameter.empty)
            for declaration in declaration_exprs(name, annotations, ret_annotation):
                self.add(declaration)
            for cls in referenced_classes([*annotations, ret_annotation]):
                for extra in class_declarations(cls):
                    self.add(extra)
            _DECLARED_DEFINES[(self._space, name)] = True
        if compiled.generator:
            _DEFINED_GENERATORS.add((self._space, name))
        return Defined(
            name, params, body, dispatcher, self,
            patterns=patterns, runtime_ops=compiled.runtime_ops,
        )

    def type(self, cls: type | None = None, *, accessors: bool = True, methods: bool = True):
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
        from . import convert as _convert

        def apply(target: type) -> type:
            registration = _convert.ensure_registered(target)
            for declaration in _convert.declarations(target):
                self.add(declaration)
            if (
                accessors
                and registration.image == "expression"
                and registration.fields
            ):
                constructor = registration.type_name
                fields = registration.fields
                variables = [Var(f"f{i}") for i in range(1, len(fields) + 1)]
                for position, field_name in enumerate(fields):
                    head = Expr(
                        [
                            Sym(f"{constructor}-{field_name}"),
                            Expr([Sym(constructor), *variables]),
                        ]
                    )
                    self.add(Expr([Sym("="), head, variables[position]]))
            if methods:
                self._register_methods(target, registration.type_name)
            return target

        return apply(cls) if cls is not None else apply

    def _register_methods(self, target: type, type_name: str) -> None:
        """Every method the class itself defines, as a MeTTa function
        named {Type}-{method}: the instance argument accepts a
        constructor term (rebuilt through the translator) or a live
        handle, and results the translator knows project back to terms."""
        import inspect as _inspect

        from . import convert as _convert
        from .atoms import Gnd, encode

        def projectable(value: Any) -> Any:
            try:
                _convert.ensure_registered(type(value))
            except TypeError:
                return value
            return _convert.project(value).atom

        def wrapper_for(fn):
            def call(instance, *args):
                subject = (
                    _convert.build(instance, target)
                    if isinstance(instance, Expr)
                    else (instance.value if isinstance(instance, Gnd) else instance)
                )
                values = [a.value if isinstance(a, Gnd) else a for a in args]
                result = fn(subject, *values)
                if result is None:
                    return None
                if isinstance(result, Atom):
                    return result
                if isinstance(result, (bool, int, float, str)):
                    return encode(result)
                return projectable(result)

            return call

        for method_name, fn in vars(target).items():
            if method_name.startswith("_") or not _inspect.isfunction(fn):
                continue
            parameters = list(_inspect.signature(fn).parameters.values())[1:]
            required = sum(
                1 for p in parameters if p.default is _inspect.Parameter.empty
            )
            arities = list(range(1 + required, len(parameters) + 2))
            self.op(
                wrapper_for(fn),
                name=f"{type_name}-{method_name}".replace("_", "-"),
                typed=False,
                pass_atoms=True,
                arities=arities,
            )

    def fn(self, name: str) -> "_EngineFunction":
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


def _serializable(atom: Atom) -> bool:
    from .atoms import Gnd

    stack = [atom]
    while stack:
        current = stack.pop()
        if isinstance(current, Gnd) and not isinstance(
            current.value, (bool, int, float, str)
        ):
            return False
        if isinstance(current, Expr):
            stack.extend(current.children)
    return True


def _guard_against(body: Atom, earlier: list, patterns: dict, params: list) -> Atom:
    """The current clause's body, declining every earlier literal head.

    For each earlier clause, the inputs it claims are the positions it fixed
    with literals; when this clause leaves all of those positions variable,
    the two overlap, and this clause answers (empty) there, so dispatch reads
    first-match the way the stacked Python reads.
    """
    from .atoms import Gnd

    for earlier_patterns in earlier:
        if not earlier_patterns:
            continue
        overlapping = all(
            p not in patterns or patterns[p] == v for p, v in earlier_patterns.items()
        )
        contested = [p for p in earlier_patterns if p not in patterns]
        if not overlapping or not contested:
            continue
        condition: Atom | None = None
        for p in contested:
            test = Expr([Sym("=="), Var(p), earlier_patterns[p]])
            condition = test if condition is None else Expr([Sym("and"), condition, test])
        body = Expr([Sym("if"), condition, Expr([Sym("empty")]), body])
    return body


class _Assuming:
    """Facts scoped to a with-block; see MeTTa.assuming."""

    __slots__ = ("_space", "_facts")

    def __init__(self, space: MeTTa, facts: list[Atom]) -> None:
        self._space = space
        self._facts = facts

    def __enter__(self) -> MeTTa:
        self._space.add(*self._facts)
        return self._space

    def __exit__(self, exc_type, exc, tb) -> None:
        for fact in self._facts:
            self._space.remove(fact)


class _StatsBlock:
    """MeTTa.stats(): engine counter deltas over one with-block.

    Before exit the fields are None; after exit they carry the deltas the
    block spent: inferences (int), cputime (seconds), walltime (seconds,
    Python's perf_counter), gc_count, gc_freed (bytes), gc_time (seconds),
    and table_bytes (answer-table bytes the block grew or, negative,
    released; tabling's memory made visible where the counters live).
    """

    __slots__ = (
        "_rt", "_before", "_wall",
        "inferences", "cputime", "walltime", "gc_count", "gc_freed", "gc_time",
        "table_bytes",
    )

    def __init__(self, rt: Runtime) -> None:
        self._rt = rt
        self._before = None
        self._wall = None
        self.inferences = None
        self.cputime = None
        self.walltime = None
        self.gc_count = None
        self.gc_freed = None
        self.gc_time = None
        self.table_bytes = None

    def __enter__(self) -> "_StatsBlock":
        import time

        self._before = self._rt.apply_must("petta_py_stats")
        self._wall = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        import time

        wall = time.perf_counter() - self._wall
        after = self._rt.apply_must("petta_py_stats")
        inferences, cputime, gc_count, gc_freed, gc_ms, table_bytes = (
            a - b for a, b in zip(after, self._before)
        )
        # The two petta_py_stats crossings themselves sit inside the
        # window; their cost is a few hundred inferences, the noise floor.
        self.inferences = int(inferences)
        self.cputime = float(cputime)
        self.walltime = wall
        self.gc_count = int(gc_count)
        self.gc_freed = int(gc_freed)
        self.gc_time = float(gc_ms) / 1000.0
        self.table_bytes = int(table_bytes)

    def __repr__(self) -> str:
        if self.inferences is None:
            return "<stats: pending>"
        return (
            f"<stats: {self.inferences} inferences, "
            f"{self.cputime:.4f}s cpu, {self.walltime:.4f}s wall>"
        )


class Cursor:
    """MeTTa.stream(): answers pulled one at a time from an engine-held
    query. Iterate it, close() it, or leave its with-block; exhaustion
    closes it by itself, a second close is a no-op, and a cursor dropped
    unclosed is reaped by its finalizer. Rows carry the query's variable
    names as columns, exactly as query()'s rows do.
    """

    __slots__ = ("columns", "_row_cls", "_timeout", "_rt", "_handle", "_closed", "_finalizer", "__weakref__")

    def __init__(
        self,
        space: "MeTTa",
        patterns: tuple,
        where: Any | None,
        timeout: float | None,
        inferences: int | None,
    ) -> None:
        atoms = [_to_atom(p) for p in patterns]
        columns: list[str] = []
        for a in atoms:
            for name in variables(a):
                if name != "_" and name not in columns:
                    columns.append(name)
        self.columns = tuple(columns)
        self._row_cls = _row_class(self.columns)
        limits = _limits(timeout, inferences)
        # The inference budget rides inside the engine (its work is its
        # own counter's, invisible to a per-pull wrapper); the wall bound
        # wraps each pull outside, where idle time between pulls is free.
        self._timeout = None if limits is None or limits[0] < 0 else limits[0]
        steps = -1 if limits is None else limits[1]
        self._rt = space.runtime
        wires = [a.to_wire() for a in atoms]
        guard = [] if where is None else _to_atom(where).to_wire()
        self._handle = self._rt.apply_must(
            "petta_py_cursor_open", space.space_name, wires, guard, list(columns), steps
        )
        self._closed = False
        # The finalizer is the last guard, not the contract: it destroys
        # the engine if a cursor is dropped unclosed, from whichever
        # thread collection runs on (cross-thread destroy is probed).
        self._finalizer = weakref.finalize(self, Cursor._reap, self._handle)

    @staticmethod
    def _reap(handle: Any) -> None:
        import petta as pkg

        try:
            pkg.janus.query_once("petta_py_cursor_close(E)", {"E": handle})
        except Exception:
            pass  # the engine is already gone, or the process is ending

    def __iter__(self) -> "Cursor":
        return self

    def __next__(self):
        if self._closed:
            raise PettaError("this cursor is closed")
        if self._timeout is None:
            answer = self._rt.apply_must("petta_py_cursor_next", self._handle)
        else:
            answer = self._rt.apply_must(
                "petta_py_limited", self._timeout, -1,
                "petta_py_cursor_next", [self._handle],
            )
        if not answer:
            self.close()
            raise StopIteration
        return self._row_cls(from_wire(v) for v in answer[0])

    def close(self) -> None:
        """Destroy the held engine; idempotent, and exhaustion calls it."""
        if self._closed:
            return
        self._closed = True
        self._finalizer()  # runs the reap exactly once; later GC is a no-op

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self._closed else "open"
        return f"<cursor {state} -> {', '.join(self.columns)}>"


class EngineProfile:
    """MeTTa.profile()'s second answer: the sampler's counters and one
    row per predicate, self-ticks-descending. Each node is (predicate,
    calls, redos, ticks_self, ticks_siblings)."""

    __slots__ = ("samples", "ticks", "nodes")

    def __init__(self, samples: int, ticks: int, nodes: list) -> None:
        self.samples = int(samples)
        self.ticks = int(ticks)
        self.nodes = [tuple(node) for node in nodes]

    def top(self, n: int = 10) -> list[tuple]:
        """The n predicates the samples landed in most."""
        return self.nodes[:n]

    def __repr__(self) -> str:
        return (
            f"<profile: {self.samples} samples, {self.ticks} ticks, "
            f"{len(self.nodes)} predicates>"
        )


class Prepared:
    """A prepared query: pattern wires and columns built once, solved many
    times, optionally with per-call facts. The ladder the clingo API walks
    (assumptions per solve, inputs per session, rules added), with the rung
    clingo lacks: rules REMOVED, since this engine erases clauses whole.

        route = m.prepare(S.path(V.a, V.b))
        route.solve()
        route.solve(given=[S.edge(S.a, S.b)])   # facts for this call only
    """

    __slots__ = ("_space", "_patterns", "_where", "_wires", "_guard", "columns")

    def __init__(self, space: MeTTa, patterns: list[Atom], where: Atom | None) -> None:
        self._space = space
        self._patterns = patterns
        self._where = where
        self._wires = [p.to_wire() for p in patterns]
        self._guard = None if where is None else where.to_wire()
        columns: list[str] = []
        for pattern in patterns:
            for name in variables(pattern):
                if name != "_" and name not in columns:
                    columns.append(name)
        self.columns = tuple(columns)

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
        MeTTa.query()."""
        if not given:
            return self._run(limit, timeout, inferences)
        with self._space.assuming(*given):
            return self._run(limit, timeout, inferences)

    def _run(self, limit: int | None, timeout: float | None, inferences: int | None) -> Rows:
        rt = self._space.runtime
        space = self._space.space_name
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
            answered = rt.apply_must("petta_py_limited", *limits, pred, ins)
        decoded = [tuple(from_wire(v) for v in r) for r in answered]
        return Rows(self.columns, decoded)

    def __repr__(self) -> str:
        shown = ", ".join(str(p) for p in self._patterns)
        return f"<prepared {shown} -> {', '.join(self.columns)}>"


class _EngineFunction:
    """One engine function, callable the way Python callables are."""

    __slots__ = ("_space", "_name")

    def __init__(self, space: MeTTa, name: str) -> None:
        self._space = space
        self._name = name

    def _term(self, args: tuple) -> Expr:
        return Expr([Sym(self._name), *(encode(a) for a in args)])

    def __call__(self, *args: Any) -> Any:
        answers = self._space.eval(self._term(args))
        if len(answers) != 1:
            raise ValueError(
                f"({self._name} ...) answered {len(answers)} results; calling "
                f"expects exactly one. Use .all(...) for every answer."
            )
        return answers[0]

    def all(self, *args: Any) -> list:
        return self._space.eval(self._term(args))

    def __repr__(self) -> str:
        return f"<engine function {self._name} on {self._space.space_name}>"
