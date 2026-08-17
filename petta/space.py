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
  - public name and save-format annotations distinguish their string
    contexts [tested test_public_context_types_are_distinct]
  - cast preserves a concrete target class as its static return type and keeps
    the target positional-only [tested
    test_target_type_overloads_preserve_the_requested_class,
    test_cast_target_is_positional_only]
  - dropping a space releases its integration installation records [tested
    test_dropped_space_name_reinstalls_integrations]
  - eval_status and run_status separate a pruned branch from an unevaluated
    term, and strict= refuses only the latter [tested
    test_eval_status_reports_the_four_outcomes,
    test_strict_accepts_a_pruned_branch_and_every_reduction]
  - profile_extension reports every declared member of an extension, including
    one the workload never reached, with the tier that installed it and its
    clause index [tested 2026-08-16:
    test_profile_extension_reports_every_declared_member,
    test_profile_extension_separates_an_indexed_table_from_a_single_clause]
  - register_prolog reads a metta_export declaration from inline source as it
    does from a file [tested 2026-08-16:
    test_inline_source_declares_its_own_exports_too]
  - del m[pattern] removes every unifying occurrence and raises KeyError
    when none unified, remove() reporting the same absence as False
    [tested test_delitem_removes_every_unifying_occurrence]
  - |= merges a space, a registered space name, or an iterable, and refuses
    an operand add() would lift into one atom [tested
    test_ior_merges_a_space_equations_included,
    test_ior_refuses_the_operands_add_would_lift]
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
import hashlib
import os
from collections import abc as _abc
from collections.abc import Callable
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    ParamSpec,
    Self,
    TypeVar,
    cast,
    overload,
)

if TYPE_CHECKING:
    # Bound to a private name: MeTTa.parallel is a method, so a bare
    # `parallel` in an annotation inside the class body resolves to it.
    from .parallel import EnginePool as _EnginePool

from . import integrate as _integrate
from . import ops as _ops_module
from ._api_types import _DEFAULT_SPACE, SaveFormat, SpaceName
from ._engine import Runtime, bridge, runtime, started
from ._space_definitions import (
    clear_definitions,
    install_define,
    install_prolog_define,
    install_type,
)
from ._space_diagnostics import derivations, explain_no_match
from ._space_execution import (
    evaluate,
    evaluate_status,
    profile_extension,
    profile_source,
    run_source,
    run_status,
    value_one,
)
from ._space_objects import (
    Cursor,
    EngineProfile,
    FunctionCost,
    Prepared,
    _Assuming,
    _EngineFunction,
    _StatsBlock,
    guard_atom,
)
from ._space_persistence import (
    load_space,
    raise_unsafe_text_symbol,
    save_space,
)
from ._space_query import query_rows
from .atoms import (
    Atom,
    Expr,
    Gnd,
    Sym,
    Undefined,
    Var,
    _to_atom,
    atom_from_wire,
    encode,
    parse,
)
from .casting import cast as _cast
from .define import Defined, PrologBacked
from .derivation import Derivation
from .errors import EngineError, PettaError, SourceNotFound, StrictError
from .foreign import (
    has_provider,
    register_provider,
    require_capability,
    unregister_provider,
)
from .lint import lint as _lint
from .results import Rows
from .subscribe import _subscriptions_for
from .subscribe import subscribe as _subscribe
from .trace import trace as _trace

__all__ = ["Cursor", "EngineProfile", "MeTTa", "Prepared", "current_space"]

_CastT = TypeVar("_CastT")
_R = TypeVar("_R")
_P = ParamSpec("_P")


def current_space(default: str = _DEFAULT_SPACE) -> SpaceName:
    """The space whose module the ENGINE is evaluating in right now.

    Callable from inside a registered operation, where it answers the space
    of the program that called it: janus re-enters the engine cleanly, so
    an operation can behave per-space without the space being an argument.
    Outside any evaluation it answers the default.
    """
    if not started():
        return SpaceName(default)
    row = bridge().query_once("current_metta_space(S)")
    return SpaceName(str(row["S"])) if row else SpaceName(default)


def _row_values(row: Any, keys: list[Any]) -> Any:
    """One table row's values, left to right.

    Iterating a mapping yields its keys, so a list of records would store
    the column names as data, once per row, with no error and the right
    row count. Records are read by their values instead, and the first
    record fixes the key order every later one must repeat, since that
    order is what decides which fact position a value lands in.
    """
    if not isinstance(row, _abc.Mapping):
        return row
    if not keys:
        keys.extend(row.keys())
    elif list(row.keys()) != keys:
        raise ValueError(
            f"every record must carry the same keys in the same order, "
            f"because their order fixes the fact positions; expected "
            f"{keys}, got {list(row.keys())}"
        )
    return row.values()


def _require_source(source: Any, called: str) -> None:
    """Refuse non-text source here rather than at the engine's reader."""
    if not isinstance(source, str):
        raise TypeError(f"{called} takes MeTTa source as a string, got {source!r}")


def _require_name(name: Any, called: str) -> None:
    """Refuse a non-string name here, where the caller can still be named.

    The engine reports one as `atom_string/2: Type error`, which names a
    Prolog builtin and the tagged null `@none` instead of the argument.
    """
    if not isinstance(name, str):
        raise TypeError(f"{called} takes a name as a string, got {name!r}")


def _source_identity(source: str | None, path: Any) -> str:
    """What the engine will record this registration's source as.

    The pre-load check needs it, because "a name another Prolog source owns"
    has to distinguish another source from THIS one re-registering. Both
    routes know it before the load: a file is its path, and inline source is
    the module name it loads under, which is what the engine reads back off
    the clauses afterwards.
    """
    if path is not None:
        return os.fspath(path)
    return _inline_module_name(str(source))


def _inline_module_name(source: str) -> str:
    """The name SWI loads inline Prolog source under.

    SWI removes every clause loaded under a name when that name is loaded
    again, so this name decides which library's clauses a later registration
    erases. It was `id(source)`, an address CPython hands to the next object
    of the same size the moment the string is freed, and a library generating
    Prolog therefore lost every predicate but the last: the reuse struck on
    the SECOND registration, not after four hundred, and the failure surfaced
    later as `findall_loop/4: Unknown procedure`.

    A content hash fixes every axis at once. It is deterministic, so two
    different sources cannot collide; it is idempotent, so registering the
    same source twice reloads it rather than accumulating clauses; and it
    means something in a stack trace.

    persistent.py hashes the journal PATH and appends a counter, because two
    providers on one journal need distinct modules. Here the requirement is
    the opposite, that the same source reuse one name, so the two do not
    share a helper.
    """
    digest = hashlib.blake2s(source.encode("utf-8"), digest_size=8).hexdigest()
    return f"petta_inline_{digest}"


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
    see the same &self state. Use new_space() when independent stored state
    is required.

    A named space isolates both its atoms and its EQUATIONS, and the rule for
    equations has a third part this docstring used to get wrong by calling
    them process-wide. They are per-space, with a dynamic fallback to &self
    and local shadowing [measured 2026-08-17]:

        equation defined in     &self       s1          s2
        ------------------      ---------   ---------   ---------
        s1                      unreduced   answers     unreduced
        &self                   answers     answers     answers
        both                    &self's     s1's        &self's

    So a helper put in &self is reachable from every space, one put in a named
    space is private to it, and a name defined in both resolves to the local
    one where it exists. Registrations are the thing that really is
    process-wide, which new_space() says.

        from petta import MeTTa, S, V

        m = MeTTa()
        m.run("(= (foo) boo) !(foo)")     # [[Sym('boo')]]
        m.add(S.Parent(S.Tom, S.Bob))
        m.query(S.Parent(V.x, S.Bob))     # Rows[x](Row(x=Sym('Tom')))
    """

    def __init__(
        self,
        space: str = _DEFAULT_SPACE,
        *,
        verbose: bool = False,
        petta_path: str | None = None,
    ) -> None:
        if not isinstance(space, str):
            raise TypeError(
                f"a space name is a string starting with &, as in &self or "
                f"&kb; got {space!r}"
            )
        if not space.startswith("&"):
            raise ValueError(
                f"a space name starts with &, as in &self or &kb; got {space!r}. "
                f"The prefix is load-bearing: is-space recognises it, and a $ "
                f"name would read back as a variable."
            )
        self._rt: Runtime = runtime(petta_path=petta_path, verbose=verbose)
        # The public parameter takes a plain str so a literal is writable;
        # the NewType is constructed once here and threads through inside.
        self._name = SpaceName(space)
        self._dropped = False
        self._ephemeral = False

    @property
    def _space(self) -> SpaceName:
        """The space name, refused once this handle has been dropped.

        Every engine call reads the name through here, so a dropped handle
        cannot reach the engine at all. That matters because drop() returns
        an anonymous name to the pool: without this, a later new_space()
        hands the same name to a new handle and writes through the dead one
        land in the new space, silently.
        """
        if self._dropped:
            raise PettaError(
                f"{self._name} was dropped; this handle is dead. Its name may "
                f"already belong to another space, so writes through it would "
                f"land there. Take a new handle from new_space() or space()."
            )
        return self._name

    # ------------------------------------------------------------------ naming

    @property
    def space_name(self) -> SpaceName:
        return self._space

    def space(self, name: str) -> MeTTa:
        """Another space on the same engine."""
        return MeTTa(name)

    def space_names(self) -> list[str]:
        """Every space name this engine registers, sorted: '&self' and
        '&petta' from boot, every native space that has been written to,
        and every foreign space currently bound. Naming a space never
        registers it, only writing or binding does, so a bind! token's
        target appears here once something is stored under it."""
        row = self._rt.once("petta_py_space_names(Names)")
        return [str(name) for name in row["Names"]]

    def new_space(self) -> MeTTa:
        """An anonymous space with a name nothing else is using.

        Works as a context manager: leaving the block drops the space, so a
        churn of short-lived spaces reuses names instead of growing the
        engine's module table.

            with m.new_space() as scratch:
                scratch.add(...)

        What it isolates is STORED STATE: atoms and equations. Registrations
        are process-wide, so a register_prolog, a register_op or a define made
        on a new space is visible from every other one. Reach for this to
        isolate the data a test writes, not the names it registers; to isolate
        a name, unregister it.
        """
        row = self._rt.must("petta_py_new_space(Name)")
        fresh = MeTTa(str(row["Name"]))
        fresh._ephemeral = True
        return fresh

    def drop(self) -> None:
        """Clear this space and release its name for reuse. Dropping a
        foreign space releases the binding and leaves the provider's own
        data alone; &self, the engine's own space, is cleared but its name
        never released. Subscriptions on the space cancel with it: a
        pooled name reused later must not deliver to the old life's
        watchers. The handle itself dies here: every later call through it
        refuses, because its name may already belong to another space.
        Dropping twice is a no-op, as closing twice is."""
        if self._dropped:
            return
        for subscription in _subscriptions_for(self._space):
            subscription.cancel()
        if has_provider(self._space):
            unregister_provider(self._rt, self._space)
        self.clear()
        if self._space != "&self":
            self._rt.must("petta_py_release_space(Space)", Space=self._space)
        _integrate._forget_space(self._space)
        self._dropped = True

    def __enter__(self) -> Self:
        if not self._ephemeral:
            raise TypeError(
                f"{self._space} was not created by new_space(); only an "
                f"anonymous space scopes to a with-block, since leaving the "
                f"block drops it. Call drop() deliberately for a named one."
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.drop()

    def __repr__(self) -> str:
        state = ", dropped" if self._dropped else ""
        return f"MeTTa({self._name!r}{state})"

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
        strict: bool = False,
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

        `strict=True` requires every directive to reduce, raising
        StrictError on one the engine hands back unevaluated. It is opt-in,
        because an unreduced term is an ordinary MeTTa value: a bare data
        constructor is refused under strict for the same reason a bare
        typo is, since neither reduces. An empty answer is allowed, being
        the pruned branch that (empty) and an unmatched match produce.
        eval_status() reports the same paths without refusing anything.
        """
        _require_source(source, "run")
        if strict:
            self._refuse_unreduced(
                run_status(self._rt, self._space, source, timeout, inferences)
            )
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

    def _refuse_unreduced(
        self, groups: list[list[tuple[str, Any]]]
    ) -> None:
        """Refuse any directive the engine handed back unevaluated."""
        for position, group in enumerate(groups, start=1):
            for status, answer in group:
                if status == "not-reducible":
                    raise StrictError(
                        f"{answer} is not reducible: no equation, builtin or "
                        f"special form applies to it",
                        term=answer,
                        directive=position,
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

    def profile_extension(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        extension: str | None = None,
        names: _abc.Sequence[str] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
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
            raise ValueError(
                "profile_extension takes extension= (its registered members) "
                "or names= (an explicit list), and needs exactly one of them"
            )
        wanted = (
            [str(name) for name in names]
            if names is not None
            else list(self._extension_members(extension))
        )
        return profile_extension(
            self._rt,
            self._space,
            source,
            using,
            wanted,
            timeout=timeout,
            inferences=inferences,
        )

    def _extension_members(self, extension: str | None) -> tuple[str, ...]:
        _require_name(extension, "profile_extension")
        return tuple(
            self._rt.must(
                "petta_py_extension_members(Name, Names)", Name=str(extension)
            )["Names"]
        )

    def save(
        self,
        path: str | os.PathLike[str],
        format: SaveFormat = "metta",
    ) -> int:
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
        Use clear() first or load into new_space() when replacement is wanted.
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
        refused here rather than failing silently inside.

        A variable's NAME is not stored. `(rule $x $y)` reads back as
        `(rule $_17902 $_17904)`, because a variable is an identity and not a
        spelling. That is the right property for a logic engine and it is the
        one thing about storage that surprises everybody once."""
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
        or any iterable of rows. A row may be a sequence or a mapping, so
        a list of records from rows.to_dicts() reads correctly; every
        record must carry the same keys in the same order, because their
        order is what fixes the fact positions. A mapping of columns takes
        its own key order, and columns of unequal length are a hard error
        rather than a silent truncation.

        rows.table() is the reverse in shape, the dict every DataFrame
        constructor takes, but not in identity: it decodes atoms to Python
        values, so a symbol comes back as a str and re-enters as a MeTTa
        String. For a lossless round trip keep the atoms:

            m.add_table(head, {c: rows[c] for c in rows.columns})
        """
        head_atom = _to_atom(head)
        keys: list[Any] = []
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
            Expr([head_atom, *(encode(value) for value in _row_values(row, keys))])
            for row in rows
        ]
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
        """Return the number of atoms stored in this space."""
        row = self._rt.once("petta_py_count(Space, N)", Space=self._space)
        return int(row["N"])

    @overload
    def cast(self, value: Any, type_: _builtins.type[_CastT], /) -> _CastT: ...

    @overload
    def cast(self, value: Any, type_: Atom | str, /) -> Any: ...

    def cast(self, value: Any, type_: Any, /) -> Any:
        """Answer value, narrowed to its Python-most spelling, when this
        space's type discipline admits it as type_: the same acceptance
        a typed call compiles, ':' declarations in this space and &self
        in scope, protocol types included. A refused cast raises
        petta.CastError naming the value's actual types, the loud
        spelling of what a typed call does silently."""
        return _cast(self, value, type_)

    def trace(self, source: str, max_events: int = 1_000_000):
        """Run source under the engine's reduction trace and answer
        TraceEvent records: what entered reduction at which depth, what
        it answered, and which reductions failed (a call with no exit).
        The source executes for real, writes included, like run(); the
        wrap exists only while tracing, so untraced calls pay nothing.
        max_events bounds the recording, raising past it rather than
        accumulating a long run's trace without limit."""
        return _trace(self, source, max_events=max_events)

    def lint(self):
        """Diagnose this space for the silently-wrong class: declared
        types nothing defines, arity mismatches, unbound body variables,
        duplicate equations, and references no function or fact carries.
        Answers petta.lint.Finding records, empty when nothing looks
        wrong."""
        return _lint(self)

    def digest(self) -> str:
        """A sha256 hex digest of this space's content: every stored atom,
        equations included, canonicalized (variables numbered, multiset
        sorted) so the same atoms answer the same digest in any insertion
        order and in any process. Two spaces agree on digest() exactly
        when save() would write the same content. Live host objects have
        no cross-process identity and are refused, like save()."""
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

    def __bool__(self) -> bool:
        """Always true: a space is a handle to a store, not a value that
        dwindles. Without this, bool() falls through to __len__ and an
        empty space is falsy, so `if space:` skips a perfectly good empty
        space, the bug class that made datetime stop treating midnight as
        false in 3.5."""
        return True

    def __contains__(self, atom: Any) -> bool:
        return self._rt.do("petta_py_contains", self._space, _to_atom(atom).to_wire())

    def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        clear_definitions(self)

    def __iadd__(self, atom: Any) -> Self:
        """add()'s operator spelling, one atom per use: `m += [1, 2]`
        LIFTS the list into one expression atom, exactly as m.add([1, 2])
        does, so the two spellings never read one operand two ways. The
        bulk spelling is |=, whose operand has no lifted reading."""
        self.add(atom)
        return self

    def __isub__(self, atom: Any) -> Self:
        self.remove(atom)
        return self

    def __ior__(self, other: Any) -> Self:
        """Merge into this space in one bulk crossing: every atom of
        another space, of a registered space name, or of an iterable.

            m |= other_space     # every atom, equations included
            m |= "&kb"           # the space registered under this name
            m |= [a, b, c]       # each element becomes one atom

        Equations in the merge compile on arrival, the same rule add()
        enforces. A space is a multiset, so merging a space into itself
        doubles every atom. A Mapping is refused because add(d) reads the
        same dict as ONE grounded atom and its values would silently
        vanish here; spell the reading you mean. Strings name spaces, so
        an unregistered name is a KeyError rather than a parse."""
        if isinstance(other, MeTTa):
            merged: list[Any] = other.atoms()
        elif isinstance(other, str):
            if other not in self.space_names():
                raise KeyError(
                    f"{other!r} is not a registered space name; "
                    f"space_names() lists them. To add atoms, pass an "
                    f"iterable: m |= [{other!r}]"
                )
            merged = self.space(other).atoms()
        elif isinstance(other, (bytes, bytearray, _abc.Mapping)):
            raise TypeError(
                f"|= does not read a {type(other).__name__}: add() would "
                f"lift it into one atom, and iterating it here would read "
                f"the same operand a second way. Use m.add(x) for one "
                f"atom, or spell the elements: m |= list-of-atoms"
            )
        elif isinstance(other, _abc.Iterable):
            merged = list(other)
        else:
            raise TypeError(
                f"|= merges a space, a registered space name, or an "
                f"iterable of atoms; {type(other).__name__} is none of "
                f"those"
            )
        self.add(*merged)
        return self

    def __iter__(self):
        """Iterate the stored atoms: for atom in m."""
        return iter(self.atoms())

    def __getitem__(self, pattern: Any) -> Rows:
        """Subscription is query: m[pattern] answers query(pattern), and
        m[p1, p2] arrives as a tuple, so the comma spells the join:

            rows = m[S.edge(V.a, V.b), S.edge(V.b, V.c)]

        A str key parses first, matching query()'s tolerance. A slice is
        refused: a slice of a space has no one meaning, and the bounded
        readings have their own doors, query(limit=) for a bounded answer
        set and stream() for rows pulled until you have seen enough."""
        if isinstance(pattern, slice):
            raise TypeError(
                "a space cannot be sliced; query(limit=n) bounds the "
                "answer set, stream() pulls rows until you stop"
            )
        if isinstance(pattern, tuple):
            return self.query(*pattern)
        return self.query(pattern)

    def __delitem__(self, pattern: Any) -> None:
        """del m[pattern] removes every unifying occurrence, remove()'s
        multiset semantics under deletion's mapping spelling. Nothing
        unifying raises KeyError, as del d[k] does on a missing key;
        remove() is the door that reports absence as False instead."""
        if not self.remove(pattern):
            raise KeyError(pattern)

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

        **Slicing the result is not the same thing.** query() is EAGER, so
        `query(pat)[:3]` computes every row and throws all but three away.
        Over 2,000 stored atoms that measured 26,055 inferences against 20
        for `stream(pat)[:3]`, which pulls three and stops. Reach for `limit`
        when you want a bounded answer set, and for stream() when you want to
        take rows until you have seen enough.

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
            self,
            [_to_atom(p) for p in patterns],
            guard_atom(where),
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

    def parallel(
        self,
        *targets: Any,
        timeout: float | None = None,
    ) -> list[Atom | Undefined]:
        """Evaluate every target concurrently, answering every branch's answers.

        This is the engine's `hyperpose`, the parallel twin of `superpose`:
        one SWI thread per branch through concurrent_and/2, so independent
        branches cost about one branch's wall clock rather than their sum.

            m.run("(= (sq $x) (* $x $x))")
            m.parallel(S.sq(1), S.sq(2), S.sq(3))    # 1, 4 and 9, in any order

        This is the **in-engine** fan-out: one janus call, the branches split
        below it. The other route is `pool()`, the **Python-side** fan-out
        across several engines. Reach for this one when the fan-out is a MeTTa
        expression, and for `pool()` when it is a Python loop. They compose,
        so a pool worker may itself evaluate a `parallel()`.

        (Before 2026-08-15 this docstring said in-engine fan-out was the only
        route to a second core, because every janus call took one process-wide
        lock. That lock is now per-engine, and Python threads holding their own
        engine measured 1.94x, 3.90x and 7.26x at 2, 4 and 8 threads.)

        **Answers arrive in completion order, not argument order**, because
        the branches race. Compare sets rather than sequences, and evaluate a
        `superpose` instead when order carries meaning.

        Each target is a term or its source text, as everywhere else. No
        targets answers nothing without calling the engine.

        `timeout` bounds the call and is the bound to use here. There is
        deliberately no `inferences=`: the engine's inference limit counts
        the calling thread, and `concurrent_and/2` runs every branch in a
        worker, so a limit of 50,000 does not stop two branches spending six
        million [measured 2026-08-15]. An unenforceable bound is worse than
        an absent one, so eval() over a `superpose` is the way to bound this
        work by inferences, at the cost of running it on one core.
        """
        if not targets:
            return []
        branches = Expr([_to_atom(target) for target in targets])
        # capture=False, so evaluate answers the answer list rather than the
        # (answers, text) pair its capturing overload returns.
        return cast(
            "list[Atom | Undefined]",
            evaluate(
                self._rt,
                self._space,
                Expr([Sym("hyperpose"), branches]),
                timeout,
                None,
                capture=False,
                residuals=False,
            ),
        )

    def hyperpose(
        self,
        *targets: Any,
        timeout: float | None = None,
    ) -> list[Atom | Undefined]:
        """parallel(), under the language's own name.

        (hyperpose ...) is the engine form this runs, so the Python
        surface reads MeTTa-natively; a thread pool is a space whose
        atoms are spaces, and this is how one is exercised from Python.
        """
        return self.parallel(*targets, timeout=timeout)

    def pool(self, workers: int | None = None) -> _EnginePool:
        """A pool of worker threads that each hold their own Prolog engine.

        The Python-side twin of `parallel()`. Each worker attaches its own
        engine, so the process lock that serialises the home engine does not
        apply to it and the calls genuinely run at once [measured 2026-08-15:
        1.94x, 3.90x and 7.26x at 2, 4 and 8 workers].

            m.run("(= (sq $x) (* $x $x))")
            with m.pool(workers=4) as p:
                p.map(lambda n: m.one(f"(sq {n})"), range(64))

        Use it as a context manager so every engine is released. `workers`
        defaults to os.cpu_count(). This handle stays usable from the workers:
        a MeTTa is a space name over the process runtime, not thread-owned.

        Reach for `parallel()` instead when the fan-out is a MeTTa expression
        rather than a Python loop; the two compose.
        """
        from . import parallel  # noqa: PLC0415  a declared lazy module

        return parallel.EnginePool(workers)

    def eval_status(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[tuple[str, Atom | Undefined | None]]:
        """Evaluate a term, pairing each answer with how it was produced.

            m.eval_status(S.double(4))       # [("value", Gnd(8))]
            m.eval_status(S.Point(1, 2))     # [("not-reducible", Expr(...))]
            m.eval_status(S.empty())         # [("empty", None)]

        `value` means an equation, builtin or special form applied.
        `not-reducible` means no rule applied, so the answer is the term
        itself, which is what PeTTa does with any head it cannot call.
        `empty` means the goal produced no answer at all, and its atom is
        None. Reading the last two as the same thing is the mistake this
        exists to prevent: an unevaluated term and a pruned branch look
        alike from the answers alone. An error is not a status here,
        because it arrives as an exception.
        """
        return evaluate_status(self._rt, self._space, target, timeout, inferences)

    def run_status(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[tuple[str, Atom | Undefined | None]]]:
        """run(), with each directive's answers paired with how they arose.

        The grouping and the answers are run()'s own; see eval_status() for
        what the three paths mean.
        """
        _require_source(source, "run_status")
        return run_status(self._rt, self._space, source, timeout, inferences)

    def one(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """THE answer of evaluating target, as a plain Python value.

            m.one("(+ 1 2)")            # 3
            m.one(S.fact(5))            # 120

        Exactly one answer is the contract: none or several raise naming
        the count, because a caller asking for the value has asserted
        there is one. Grounded answers unwrap to their Python values;
        symbols and structure stay atoms.

        This is one point on the answer-cardinality axis, spelled the
        same everywhere it appears: eval() takes every answer (MeTTa's
        collapse), first() takes the first and tolerates absence, one()
        demands exactly one. fn() and Rows carry the same triple, and
        the same timeout/inferences bounds apply throughout."""
        answers = self.eval(target, timeout=timeout, inferences=inferences)
        return value_one(target, answers)

    def first(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """The first answer as a plain Python value, or None for no answers.

        The tolerant member of value()'s family: value() asserts exactly
        one, eval() answers all, first() answers the first or nothing,
        decoded by the same rule as value(). An Undefined first answer
        still raises, since None here MEANS no answers.
        """
        answers = self.eval(target, timeout=timeout, inferences=inferences)
        if not answers:
            return None
        return value_one(target, answers[:1])

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

    # register returns fn unchanged, so both decorator forms are identities
    # and the two arms have to say so. Without them the bare form collapses
    # into a union that still includes the decorator-factory arm, and a call
    # through the name is checked against the factory: measured as
    # "breed(a, b) takes one argument" in evolutionary_search.py
    # [measured 2026-08-17].
    @overload
    def register_op(
        self,
        fn: Callable[_P, _R],
        /,
        *,
        name: str | None = ...,
        typed: bool = ...,
        raw: bool = ...,
        pass_atoms: bool = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
        pure: bool = ...,
    ) -> Callable[_P, _R]: ...

    @overload
    def register_op(
        self,
        *,
        name: str | None = ...,
        typed: bool = ...,
        raw: bool = ...,
        pass_atoms: bool = ...,
        arities: list[int] | None = ...,
        inverse: Callable | None = ...,
        pure: bool = ...,
    ) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...

    def register_op(
        self,
        fn: Callable | None = None,
        *,
        name: str | None = None,
        typed: bool = True,
        raw: bool = False,
        pass_atoms: bool = False,
        arities: list[int] | None = None,
        inverse: Callable | None = None,
        pure: bool = False,
    ) -> Any:
        """Register a Python callable as a MeTTa function, decorator-style.

            @m.register_op
            def double(x: int) -> int:
                return 2 * x                    # !(double 21) -> 42

            @m.register_op
            def neighbours(n: int):
                yield n - 1                     # a generator is nondeterministic
                yield n + 1

        Annotations become a (: ...) declaration unless typed=False, and the
        three combinations answer differently, which is worth knowing because
        the middle one reads like nothing happened:

            def op(x: int) -> int    typed=True   (: op (-> Number Number))
            def op(x)                typed=True   (: op (-> %Undefined% %Undefined%))
            def op(x)                typed=False  no declaration at all

        The unannotated typed=True case is not a no-op. It declares the ARROW
        SHAPE, so get-type answers that op is a one-argument function while
        constraining neither slot, and typed=False leaves get-type answering
        %Undefined%. It also costs nothing per call: a %Undefined% slot emits
        no check.

        A raw operation skips the wire encoding both ways, which suits tensor
        and number work; symbols reach it as plain strings, so keep raw off
        when the symbol-string distinction matters. pass_atoms hands the
        callable Atom objects instead of decoded Python values.
        unregister_op(name) removes every registered arity.

        The cost ladder, measured on the maintained box in inferences per
        call, is why the flags exist and which one to reach for:

            native MeTTa function            9.11   the floor
            raw=True                        10.11   opaque handles, near-native
            typed=False                     17.11   encoded values
            typed=True, literal argument    17.11   the check hoists to compile
            py-call, dotted                 22.11   the ad-hoc escape hatch

        The ergonomic default (encoded, typed) costs about 1.7x raw on the
        counter and more on wall clock, since encoding walks the value both
        ways; a registered raw operation measured 0.85us against 2.26us
        encoded. Bulk data should stay opaque: one transparent 64-float
        crossing costs 330 inferences where the handle costs 10.

        inverse gives the operation a BACKWARDS direction, so it can stand in
        a pattern position the way a MeTTa equation does:

            m.register_op(cons, name="cons", inverse=uncons)
            # !(let (cons $h $t) (1 2 3) ($h $t))  ->  (1 (2 3))

        It takes the result and returns the arguments, as a tuple, or the
        bare value at arity one; a generator enumerates every preimage, and
        None or Decline means there is none. It runs only when the arguments
        are not ground and the result is, so a forward call never reaches it,
        and an operation without one compiles exactly what it did before.

        pure=True says the operation has no effect a cache could hide, which
        is what lets it appear in a `(tabled ...)` or memoized body:

            m.register_op(len, name="size", pure=True)
            # (= (count-of $x) (size $x))  is cacheable

        It is an allow-list on purpose. An operation that does not say so is
        refused by name in a cached body, loudly, rather than cached and
        quietly wrong.
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
                inverse=inverse,
                pure=pure,
            )

        return apply(fn) if fn is not None else apply

    def unregister_op(self, name: str) -> None:
        """Remove a registered operation, every arity of it.

        An absent name raises KeyError, as convert.unregister_type does:
        removing something that was never there is a mistake worth hearing
        about, not a no-op to absorb.
        """
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
        """Report whether a function is visible from this space."""
        _require_name(name, "is_function")
        return bool(self._rt.once("petta_py_is_function(Name)", Name=name))

    def is_function_here(self, name: str) -> bool:
        """Whether a function would answer from THIS space: it has clauses
        this space's module sees, its own or the shared ones in user.
        Another space's equations are invisible here and do not count."""
        _require_name(name, "is_function_here")
        return bool(
            self._rt.once(
                "petta_py_function_visible(Space, Name)", Space=self._space, Name=name
            )
        )

    def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        row = self._rt.once("petta_py_arities(Name, As)", Name=name)
        return list(row.get("As", []))

    def register_prolog(
        self,
        source: str | None = None,
        *,
        path: str | os.PathLike[str] | None = None,
        names: _abc.Sequence[str] | _abc.Mapping[str, str] = (),
    ) -> tuple[str, ...]:
        """Register Prolog predicates as MeTTa functions, at native speed.

        This is the extension point for a library that wants to run fast.
        register_op() is the one most people find first, and every call it
        serves crosses the janus boundary: 25.16 inferences and 2.34us per
        call, against 7.16 inferences and 0.13us for the same operation
        written in Prolog [measured 2026-08-15, 3000 calls in one harness].

        Read the microseconds, not the inferences. The crossing counts as ONE
        inference and costs real time, so inferences say a Python operation is
        3.1x a Prolog one while wall clock says 18x. That is a fine price for
        reaching NumPy or an LLM and a bad one for arithmetic in a loop.

        A registered predicate keeps its nondeterminism: one that offers three
        solutions gives the MeTTa function three answers.

        A predicate follows the compiled calling convention, inputs first and
        one output last:

            m.register_prolog(
                "'vec-dot'(A, B, Out) :- ... .",
                names=["vec-dot"],
            )
            m.one("(vec-dot (1 2) (3 4))")

        or, for a library shipping a file beside its Python:

            m.register_prolog(path=Path(__file__).parent / "fast.pl",
                              names=["vec-dot", "vec-norm"])

        Every name is registered explicitly rather than discovered, because
        registering a name whose predicate is absent records no arity and then
        compiles every call to it into a partial application instead of
        failing, which is a silent wrong answer rather than an error. This
        raises instead: a name with no predicate behind it is refused before
        it can do that.

        The refusals are the engine's, through check_prolog_function_names/3
        and import_prolog_functions/2, so this and the MeTTa spelling enforce
        one rule rather than two copies of it. Three names are refused: one
        with no predicate behind it, a builtin, and a special form.

        Nothing is registered unless every name can be, so a typo in the list
        changes nothing. The consulted SOURCE does stay loaded on failure,
        which is deliberate rather than overlooked: loading it again is the
        retry, and it is idempotent, since the source is identified by a hash
        of its own content.

        **This is a method on a space and it registers PROCESS-WIDE.** So do
        register_op and define. Only equations are space-scoped, so a
        new_space() isolates one of the three things you can register and
        shares the other two. That is deliberate rather than overlooked: a
        Prolog predicate lives in `user`, every space has to be able to call
        it, and a library loaded inside a named space would define itself
        where the registration could not see it. The method sits on the space
        because that is where the rest of the surface is, not because the
        registration is scoped to it.

        The name is owned by one tier. A second registration of the same name
        from another tier is refused, in both directions, naming the owner, so
        two libraries cannot silently take the same name from each other.

        A parameter a MeTTa caller should reach unevaluated needs a type
        declaration, which this call does not take yet:

            m.register_prolog("'shape-of'(A, Out) :- Out = [shape, A].",
                              names=["shape-of"])
            m.run("(: shape-of (-> Atom Atom))")
            m.one("(shape-of (+ 1 2))")     # (shape (+ 1 2)), not (shape 3)

        Declare it BEFORE anything calls the function. A call site compiled
        while the declaration is absent keeps evaluating the argument even
        after it lands.
        """
        if (source is None) == (path is None):
            raise ValueError(
                "register_prolog takes exactly one of source or path"
            )
        if isinstance(names, _abc.Mapping):
            return self._register_renamed(path, names)
        for name in names:
            _require_name(name, "register_prolog")
        wanted = [str(name) for name in names]

        # Before the source loads, not after. Consulting a file that defines a
        # builtin's name has already replaced the engine's static predicate by
        # the time a per-name refusal could fire, so refusing afterwards left
        # (+ 1 2) answering the library's answer while this call reported the
        # registration as refused.
        if wanted:
            self._rt.must(
                "check_prolog_function_names(Names, Source, _)",
                Names=wanted,
                Source=_source_identity(source, path),
            )

        declares = "exports" if wanted else self._require_a_declaration(source, path)

        origin = self._load_prolog_source(source, path)

        # A source carrying its own :- metta_export/1 has already registered
        # by now, through the load, so a caller who declared in the file
        # passes no names at all.
        if not wanted:
            # An extension that exports nothing registers nothing, and that is
            # the shape of a provider: it contributes clauses to a seam.
            if declares == "extension":
                return ()
            return self._declared_exports(origin)

        # One goal, so the engine validates every name before it registers any:
        # a typo in the third name used to leave the first two registered and
        # callable, with the list of what had taken dying inside the exception.
        # The rule lives there rather than here, so this and the MeTTa spelling
        # cannot drift apart.
        self._rt.must("import_prolog_functions(Names, _)", Names=wanted)
        return tuple(wanted)

    def _require_a_declaration(self, source: str | None, path: Any) -> str:
        """What this source declares, read BEFORE it loads.

        It used to be consulted first and checked after, so a provider file
        with no declaration raised and installed the provider anyway: catching
        the error made everything work, which is the one outcome that teaches
        an author to ignore an error.

        All three routes are named, because pointing only at `metta_export` is
        a dead end for a provider author, who has no functions to export.
        """
        goal, inputs = (
            ("petta_py_source_declares(Source, Declares)", {"Source": os.fspath(path)})
            if path is not None
            else ("petta_py_string_declares(Text, Declares)", {"Text": str(source)})
        )
        declares = str(self._rt.must(goal, **inputs)["Declares"])
        if declares == "nothing":
            raise ValueError(
                "register_prolog needs one of three things: the names to "
                'register, a :- metta_export("...") declaration for a '
                "source that defines functions, or a "
                ":- metta_extension(name, []) declaration for one that "
                "contributes clauses to a seam and exports nothing, such "
                "as a space provider. Discovering the names would "
                "silently register whatever else the source defines"
            )
        return declares

    def _register_renamed(
        self, path: Any, renames: _abc.Mapping[Any, Any]
    ) -> tuple[str, ...]:
        """Import a Prolog module's exports under names of your choosing.

        The one collision a name refusal cannot fix is two libraries that both
        export `norm/2`: neither is wrong and neither can be asked to change.
        SWI has resolved it for thirty years with a renaming import list, and
        this is that, so the second library arrives as `libb-norm` and neither
        is rebound. Without it SWI refuses the second import, prints "No
        permission to import ... (already imported from ...)" and continues,
        leaving the newcomer silently bound to the incumbent's code.

        The arity comes from the module's own export list, so a rename names
        only the two names, and a name the module does not export is refused
        with the list of what it does export.
        """
        if path is None:
            raise ValueError(
                "renaming imports a Prolog MODULE, which SWI's import list "
                "names as a file, so it needs path= rather than source="
            )
        pairs = []
        for exported, metta_name in renames.items():
            _require_name(exported, "register_prolog")
            _require_name(metta_name, "register_prolog")
            pairs.append([str(exported), str(metta_name)])
        wanted = [pair[1] for pair in pairs]
        # Before the load, for the reason the unrenamed path documents.
        self._rt.must(
            "check_prolog_function_names(Names, Source, _)",
            Names=wanted,
            Source=os.fspath(path),
        )
        self._rt.must(
            "use_module_global(File, Renames)",
            File=os.fspath(path),
            Renames=pairs,
        )
        self._rt.must("import_prolog_functions(Names, _)", Names=wanted)
        return tuple(wanted)

    def _load_prolog_source(self, source: str | None, path: Any) -> str:
        """Load the source and answer the name the engine knows it by."""
        if path is not None:
            source_path = os.fspath(path)
            if not Path(source_path).is_file():
                raise SourceNotFound(f"no Prolog source at {source_path!r}")
            self._rt.consult(source_path)
            return source_path
        # The name the load runs under, not a constant. A declaration inside
        # the source records itself under prolog_load_context/2's answer, which
        # for a stream load is this module name, so asking under any other name
        # found nothing and a source declaring its own exports inline was told
        # it had declared none.
        module = _inline_module_name(str(source))
        self._rt.consult(module, data=str(source))
        return module

    def _declared_exports(self, origin: str) -> tuple[str, ...]:
        row = self._rt.must("petta_py_declared_exports(Source, Names)", Source=origin)
        declared = tuple(str(name) for name in row.get("Names", []))
        if not declared:
            raise ValueError(
                "register_prolog needs the names to register, or a "
                ':- metta_export("...") declaration in the source. '
                "Discovering them would silently register whatever else "
                "the source defines"
            )
        return declared

    def register_foreign_library(
        self,
        path: str | os.PathLike[str],
        *,
        entry: str | None = None,
        names: _abc.Sequence[str] = (),
    ) -> tuple[str, ...]:
        """Load a compiled `.so` and register its predicates as MeTTa functions.

        The C tier is the cheapest one on this page's cost table, one
        inference per call, and reaching it used to mean hand-writing two
        Prolog directives into `register_prolog`:

            m.register_foreign_library(Path(__file__).parent / "cbump.so",
                                       entry="install_cbump", names=["c-bump"])

        `entry` is the C initialiser, `install_cbump` in
        `install_t install_cbump(void)`; leave it out for a library whose
        entry is plain `install`.

        The path is resolved to an ABSOLUTE one here, which is the trap this
        exists to close: `use_foreign_library/2` accepts a path relative to
        the working directory, resolves it, and SWI deprecates that and warns
        on every load, so a library that shipped one worked from the repo root
        and warned or failed anywhere else. A file that is not there is
        refused here rather than inside the engine's loader.

        Everything after the load is `register_prolog`, so the same refusals
        apply: a name with no predicate behind it, a builtin, a special form,
        and a name another tier owns.
        """
        # resolve() rather than abspath(), which is the ruff-suggested spelling
        # and the better one here: the path is embedded in the use_foreign_library
        # goal below, so following a symlink to the real object is what the
        # loader wanted anyway.
        resolved = str(Path(os.fspath(path)).resolve())
        if not Path(resolved).is_file():
            raise SourceNotFound(f"no compiled library at {resolved!r}")
        load = (
            f"use_foreign_library('{resolved}')"
            if entry is None
            else f"use_foreign_library('{resolved}', {entry})"
        )
        return self.register_prolog(
            f":- use_module(library(shlib)).\n:- {load}.\n", names=names
        )

    def register_library_path(self, directory: Any, name: str) -> None:
        """Point MeTTa at a directory of files your package ships.

            # in your package's __init__
            m.register_library_path(Path(__file__).parent / "prolog", "pettorch")

        Subject first, as every register_* call: the directory being
        registered, then the library name it serves.

        `(library pettorch fast.pl)` then resolves, from MeTTa and from
        `register_prolog(path=...)`. Without it a pip-installed library is
        under neither `<engine>/../lib` nor a git checkout, so it has to pass
        absolute paths and compute them from `__file__` by hand.

        This is SWI's own `file_search_path/2`, so an alias registered here is
        one every SWI tool already understands, and aliases compose: the
        second argument of one may be another alias. Registering the same
        directory twice is a no-op; a directory that is not there is refused
        here rather than at the first import that needs it.
        """
        _require_name(name, "register_library_path")
        self._rt.must(
            "register_metta_library_path(Alias, Directory, _)",
            Alias=str(name),
            Directory=os.fspath(directory),
        )

    def unregister_prolog(self, extension: str) -> tuple[str, ...]:
        """Release everything one extension registered, and its clauses.

        The unit is the extension, not the name. `register_prolog` used to
        load a bunch of loose predicates: the engine recorded that each name
        was a function and nothing at all about the library it came from, so
        there was no uninstall to write and a partly-failed registration left
        debris nobody could enumerate.

            :- metta_extension(pettorch, [version('0.3.1')]).
            :- metta_export("(: vec-dot (-> Number Number Number))").

            m.register_prolog(path="fast.pl")     # names come from the file
            m.unregister_prolog("pettorch")       # everything it installed

        PostgreSQL's rule, and its reason: an individual member cannot be
        dropped on its own, only the whole extension, which is what stops one
        registry keeping a claim on a name another route already replaced.
        The clauses go too, through SWI's own `unload_file/1`, so a name is
        not left callable through a predicate nothing records.

        Answers the names it released. Raises when no extension of that name
        is loaded, rather than reporting success for a no-op.
        """
        _require_name(extension, "unregister_prolog")
        released = self._rt.must(
            "petta_py_extension_members(Name, Names)", Name=str(extension)
        )
        names = tuple(str(name) for name in released.get("Names", []))
        self._rt.must("petta_py_unregister_extension(Name)", Name=str(extension))
        return names

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
        return _subscribe(self._rt, self._space, _to_atom(pattern), callback, on)

    def prolog(self) -> None:
        """Drop into the engine's own interactive Prolog toplevel, the
        deepest debugging lever there is: listing/1 shows compiled
        equations, trace/0 steps through them, and quitting the toplevel
        returns here with the session intact. janus's own janus.prolog(),
        surfaced where the debugging happens.

        This is the only Prolog-facing surface here besides register_prolog,
        and that is a decision rather than a gap. There is no public
        "call any Prolog goal" method: the supported way to reach your own
        Prolog from Python is to register it and call it as a MeTTa function,
        which keeps one set of conversion rules, one error taxonomy and one
        lock. A raw goal is janus's job and janus is importable directly."""
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

    @overload
    def define(self, fn: Callable[_P, _R], /) -> Defined[_P, _R]: ...

    @overload
    def define(
        self, *, prolog: str | os.PathLike[str]
    ) -> Callable[[Callable[_P, _R]], PrologBacked[_P, _R]]: ...

    def define(
        self,
        fn: Callable[..., Any] | None = None,
        *,
        prolog: str | os.PathLike[str] | None = None,
    ) -> Any:
        """Compile a Python function into MeTTa equations, decorator-style.

        With `prolog=`, the Prolog file is registered and becomes the
        function, and the Python stays as the reference twin rather than
        being compiled:

            @m.define(prolog=Path(__file__).parent / "fast.pl")
            def vec_dot(a, b):
                return sum(x * y for x, y in zip(a, b))

            m.one("(vec-dot (1 2) (3 4))")    # the Prolog answers
            vec_dot.py((1, 2), (3, 4))          # the reference answers

        Rewriting a defined function in Prolog for speed used to mean
        deleting the Python and the differential oracle with it. Here both
        are declared together and `petta.testing.check_twin` proves they
        agree on ground inputs. The file must register the function's own
        MeTTa name and at the twin's arity, inputs then one output, and
        says so if it does not; its `metta_export` declaration owns the
        types, so annotations on the Python are documentation only.

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
        if prolog is not None:
            if fn is not None:
                raise TypeError(
                    "define(prolog=...) is applied as a decorator, so the "
                    "function comes from the definition below it"
                )
            return lambda function: install_prolog_define(self, function, prolog)
        if fn is None:
            raise TypeError("define takes a function, or prolog= and then one")
        # The annotation widened to Callable so the overloads can carry the
        # decorated signature through. install_definition still refuses
        # anything without Python source, which is where the narrowing the
        # annotation used to imply is actually enforced
        # [tested test_define_refuses_callable_objects].
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
        return _integrate.integrate(self, target)

    def register_space(self, provider: Any, name: str) -> Any:
        """A space answered by Python: matches, adds and removals route to
        the provider, so a table, a dataframe or a service is matchable the
        way stored atoms are. See petta.foreign.SpaceProvider.

        Subject first, as every register_* call: the thing being
        registered, then where it lives. The two calls that named the
        name first were the surface's own inconsistency, and learning
        the order from register_op raised TypeError here.
        """
        register_provider(self._rt, name, provider)
        return provider

    def unregister_space(self, name: str) -> None:
        """Remove a registered Python-backed space."""
        unregister_provider(self._rt, name)

    def declare_handles(
        self,
        name: str,
        pattern: str | Atom,
        fidelity: Literal["Exact", "Partial", "Sound", "Refuse"],
        *,
        det: str | None = None,
    ) -> Atom:
        """Declare how faithfully a space answers queries of one shape.

        The declaration is one (handles ...) atom in &petta, and queries
        are routed by the most specific declared shape that matches:
        Exact licenses pushing the caller's bound to the provider, Partial
        and Sound stay candidates the engine re-unifies, and Refuse makes
        the query a loud error instead of a silent partial answer. Write
        (in $x) at a position to match only queries arriving with it
        bound, so a scan-only source is three words:

            m.declare_handles("&rows", "(edge (in $a) $b)", "Refuse")

        Coherence is checked eagerly in the same transaction as the
        write: a new entry that can disagree with an existing one on some
        query fails here, naming both, rather than on the first query
        that falls into their overlap. The atom is returned; removing it
        from &petta withdraws the declaration.
        """
        if fidelity not in ("Exact", "Partial", "Sound", "Refuse"):
            raise ValueError(
                f"fidelity is one of Exact, Partial, Sound or Refuse, "
                f"not {fidelity!r}: it is the declared claim the router "
                f"acts on, so an unknown word would silently declare "
                f"nothing"
            )
        if det is not None and det not in ("det", "semidet", "nondet"):
            raise ValueError(
                f"det is det, semidet or nondet, not {det!r}: the same "
                f"vocabulary declare_function_determinism uses everywhere "
                f"else"
            )
        shape = parse(pattern) if isinstance(pattern, str) else _to_atom(pattern)
        children = [Sym("handles"), Sym(str(name)), shape, Sym(fidelity)]
        if det is not None:
            children.append(Sym(det))
        atom = Expr(children)
        self._rt.must(
            "petta_py_declare_handles(Space, W, Ctx)",
            Space="&petta",
            W=atom.to_wire(),
            Ctx=str(name),
        )
        return atom

    def declare_annotations(
        self,
        name: str,
        semiring: Literal["bool", "bag", "set", "ranked", "prob", "prov"],
    ) -> Atom:
        """Declare the semiring a context's answer annotations live in.

        A context is a space name or an operation name. bool is the
        default at which everything vanishes; ranked admits ordered
        annotations, which is what (top k ...) consumes. Declaring
        replaces any earlier declaration for the context, so the reader
        never meets two disagreeing atoms.
        """
        if semiring not in ("bool", "bag", "set", "ranked", "prob", "prov"):
            raise ValueError(
                f"semiring is one of bool, bag, set, ranked, prob or prov, "
                f"not {semiring!r}: it decides how annotations combine and "
                f"compare, so an unknown word would silently declare nothing"
            )
        previous = Expr([Sym("annotations"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("annotations"), Sym(str(name)), Sym(semiring)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_source(
        self,
        name: str,
        kind: Literal["linear", "repeated", "peek"],
    ) -> Atom:
        """Declare a space's consumption discipline.

        repeated is the default: the source re-enumerates. linear is a
        one-shot source, a cursor or a feed: its SECOND consumption is a
        loud error naming the space, where the undeclared floor answers a
        silently empty set from the drained object; re-registering the
        provider resets the mark, because a fresh provider is a fresh
        source. peek promises reads do not consume, which the conformance
        kit checks by enumerating twice.
        """
        if kind not in ("linear", "repeated", "peek"):
            raise ValueError(
                f"kind is linear, repeated or peek, not {kind!r}"
            )
        previous = Expr([Sym("source"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("source"), Sym(str(name)), Sym(kind)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_on_error(
        self,
        name: str,
        pattern: str | Atom,
        mode: Literal["keep", "empty", "abort"],
    ) -> Atom:
        """Declare what a context's failure becomes, per query shape.

        abort is the undeclared floor: the provider's error propagates.
        keep delivers the failure as one (Error <query> <reason>) answer
        beside the answers that already streamed, the language's own
        error-as-alternative reading. empty ends the stream silently, BY
        declaration, which is what separates it from a swallowed error.
        Shapes route most-specific-first exactly as (handles ...) entries
        do. Control signals and transport failures are never kept or
        emptied: an interrupt is the caller's, and an absent backend has
        said nothing about the data.
        """
        if mode not in ("keep", "empty", "abort"):
            raise ValueError(f"mode is keep, empty or abort, not {mode!r}")
        shape = parse(pattern) if isinstance(pattern, str) else _to_atom(pattern)
        atom = Expr([Sym("on-error"), Sym(str(name)), shape, Sym(mode)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_merge(
        self,
        pattern: str | Atom,
        policy: Literal["depth", "fair", "best-first"],
    ) -> Atom:
        """Declare how the engine merges one query shape's answers
        ACROSS contexts, for the multi-context idiom
        (match (superpose (&a &b)) ...).

        depth is today's space-after-space order and the undeclared
        floor. fair interleaves the streams round-robin. best-first is a
        k-way ordered merge by annotation, sound only when every merged
        context declares (emits <ctx> best-first), and loudly refused
        without. Shapes route most-specific-first as everywhere.
        """
        if policy not in ("depth", "fair", "best-first"):
            raise ValueError(
                f"policy is depth, fair or best-first, not {policy!r}"
            )
        shape = parse(pattern) if isinstance(pattern, str) else _to_atom(pattern)
        atom = Expr([Sym("merge"), shape, Sym(policy)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_context(
        self,
        name: str,
        world: Literal["closed-world", "open-world"],
    ) -> Atom:
        """Record what a space's absence means.

        Negation as failure reads absence as falsity, which is only
        sound over a world the answerer holds whole, so a negated goal
        may consult a foreign space only when it declares closed-world;
        an undeclared one refuses under negation loudly. Native spaces
        are the engine's own database and closed by construction.
        """
        if world not in ("closed-world", "open-world"):
            raise ValueError(
                f"world is closed-world or open-world, not {world!r}"
            )
        previous = Expr([Sym("context"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("context"), Sym(str(name)), Sym(world)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_reaction(
        self,
        name: str,
        pattern: str | Atom,
        operation: str | Atom,
    ) -> Atom:
        """Declare a reaction, stored as an (on ...) atom: when an atom
        matching PATTERN lands in the space, OPERATION runs under the
        match's bindings.

        The managed heads are (insert <ctx> <atom>), (retract <ctx>
        <atom>) and (revise <ctx> <old> <new>), engine-routed rules
        going through the same write paths as direct writes. Declaring
        installs the engine's write hook, which is why reactions go
        through here or petta_install_bridges rather than a bare
        add-atom.

        petta.bridge() is the NEIGHBOUR, not a special case of this: a
        reaction's operation runs engine-side, so it reaches registered
        spaces, while a bridge rule delivers Python-side to anything
        with add and remove, an unregistered or remote target included.
        Same multi-context-systems idea, two delivery tiers.
        """
        shape = parse(pattern) if isinstance(pattern, str) else _to_atom(pattern)
        op = parse(operation) if isinstance(operation, str) else _to_atom(operation)
        atom = Expr([Sym("on"), Sym(str(name)), shape, op])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        self._rt.must("petta_install_bridges")
        return atom

    def declare_admits(self, name: str, type_name: str) -> Atom:
        """Type a pool's membership: only TYPE-carrying atoms enter.

        A thread pool is a space whose atoms are spaces, and this is its
        door: (admits &pool Space) plus per-atom (: <space> Space)
        declarations make membership a type judgement the ontology
        already knows how to make.
        """
        previous = Expr([Sym("admits"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("admits"), Sym(str(name)), Sym(type_name)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        self._rt.must("petta_install_admission")
        return atom

    def declare_capacity(self, name: str, limit: int) -> Atom:
        """Bound a pool: an add beyond LIMIT atoms is refused loudly."""
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError(f"capacity is a positive integer, not {limit!r}")
        previous = Expr([Sym("capacity"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("capacity"), Sym(str(name)), Gnd(limit)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        self._rt.must("petta_install_admission")
        return atom

    def declare_writes(
        self,
        name: str,
        atomicity: Literal["transactional", "atomic-single", "best-effort"],
    ) -> Atom:
        """Declare what a space's writes promise inside a transaction.

        transactional providers implement petta.foreign.Transactional and
        are committed or rolled back WITH the engine's transaction;
        best-effort is the author's declared acceptance of a write that
        survives a rollback; atomic-single refuses transactional writes.
        Undeclared spaces refuse them loudly too, because a foreign write
        silently surviving a rolled-back transaction is the wrong answer
        the declaration exists to replace.
        """
        if atomicity not in ("transactional", "atomic-single", "best-effort"):
            raise ValueError(
                f"atomicity is transactional, atomic-single or best-effort, "
                f"not {atomicity!r}"
            )
        previous = Expr([Sym("writes"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("writes"), Sym(str(name)), Sym(atomicity)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    def declare_emits(
        self,
        name: str,
        policy: Literal["depth", "fair", "best-first"],
    ) -> Atom:
        """Declare the order a context emits its own answers in.

        best-first is the promise (top k ...) needs before its bound may
        reach the provider: the first k of a best-first emission ARE the
        k best. Distinct from the (merge <pattern> <policy>) strategy,
        which is how the ENGINE merges answers across several contexts.
        """
        if policy not in ("depth", "fair", "best-first"):
            raise ValueError(
                f"policy is depth, fair or best-first, not {policy!r}"
            )
        previous = Expr([Sym("emits"), Sym(str(name)), Var("old")])
        self._rt.once(
            "petta_py_remove(Space, W, _)",
            Space="&petta",
            W=previous.to_wire(),
        )
        atom = Expr([Sym("emits"), Sym(str(name)), Sym(policy)])
        self._rt.must(
            "petta_py_add(Space, W)", Space="&petta", W=atom.to_wire()
        )
        return atom

    # ------------------------------------------------------------ interop

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface."""
        return self._rt
