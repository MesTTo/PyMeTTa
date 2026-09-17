"""Purpose: mutate space contents and implement their Python collection protocols.

Guarantees: from_ adds an ordinary live reference row through the existing
write door [tested: test_from_is_a_live_stored_row; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
"""

from __future__ import annotations

import builtins as _builtins
from collections import abc as _abc
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, overload

import metta._spaces.cursor as _spaces_cursor_module
import metta._spaces.execution as _spaces_execution_module
import metta._spaces.intents as _spaces_intents_module
import metta._spaces.results as _spaces_results_module
import metta._spaces.scope as _spaces_scope_module
import metta._spaces.snapshot as _spaces_snapshot_module
import metta.doors as _doors
from metta._atoms.designation import _DEFAULT_SPACE, _CastT, _SpaceT
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Handle,
    Symbol,
    Variable,
    _atom_from_wire,
    _to_atom,
)
from metta._atoms.library import Library, import_library
from metta._errors.errors import EngineError, Timeout
from metta._lazy import lazy


def _copies_after_its_base(atom: Any) -> bool:
    """Whether a copied atom is a specializer-generated equation.

    The engine spells every generated head with the `_Spec_` infix, so the
    infix is the marker; a user function that happens to carry it is merely
    ORDERED after the others, never dropped, so the heuristic cannot lose an
    atom.
    """
    try:
        if not isinstance(atom, Expression) or str(atom.head) != "=":
            return False
        lhs = atom.args[0]
        return isinstance(lhs, Expression) and "_Spec_" in str(lhs.head)
    except (AttributeError, IndexError):
        return False

def _fact_stream(value: Any) -> Iterator[Any] | None:
    """Classify one ``+=`` operand without mistaking semantic atoms for rows.

    Precedence is the contract. A constructed Atom, including iterable
    Expression and Space handles, is one atom. Text, bytes, mappings, Paths,
    and values with an explicit ``__metta__`` conversion are scalar too.
    Dataframes expose rows through their row protocol rather than their generic
    iterator. An outer tuple made only of complete tuple/Expression rows is a
    fact stream; any other nonempty tuple is one transparent Expression. Empty
    tuple joins the empty iterable law, while ``Expression()`` remains the
    unambiguous spelling for one empty expression atom.

    The final ``iter(value)`` is deliberate: Python's legacy ``__getitem__``
    protocol is iterable even when ``isinstance(value, Iterable)`` is false.
    """
    if isinstance(value, (Atom, Library)):
        return None
    if isinstance(value, lazy('metta._declare.rules').Rules):
        return iter(value)

    iter_rows = getattr(value, "iter_rows", None)
    if callable(iter_rows):
        return iter(iter_rows())
    itertuples = getattr(value, "itertuples", None)
    if callable(itertuples):
        return iter(itertuples(index=False))

    if isinstance(value, tuple):
        if not value or all(isinstance(item, (Expression, tuple)) for item in value):
            return iter(value)
        return None
    if isinstance(value, (str, bytes, bytearray, _abc.Mapping, Path)):
        return None
    if getattr(type(value), "__metta__", None) is not None:
        return None
    try:
        return iter(value)
    except TypeError:
        return None

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/ext/metta-arrays/tests/test_arrays.py::test_embedding_store_validates_added_vectors', 'extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_add_atom_accepts_a_computed_space_handle', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_add_query_atoms'),
    alias='add',
    binding=_doors.Binding('metta_py_add_many', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:add]'),),
)
def add(space: _root.Space, *atoms: Any) -> None:
    """Add atoms to this space, one engine round-trip for the lot.
    An (= ...) atom compiles as an equation. Every Atom shape crosses
    unchanged, including a bare Symbol, Grounded value, and empty
    Expression; a free Variable receives the engine's own
    insufficient-instantiation refusal. The MeTTa longhand is
    `!(add-atoms <space> (<atom> ...))`. It is NOT `add-atom`, which is
    upstream PeTTa's spelling and takes upstream's domain: a headless atom
    cannot become a fact in a space there, so `!(add-atom &self b)` has no
    answer on either engine. This space is wider and `add-atoms` is the
    door onto the wider part.

    A variable's NAME is not stored. `(rule $x $y)` reads back as
    `(rule $_17902 $_17904)`, because a variable is an identity and not a
    spelling. That is the right property for a logic engine and it is the
    one thing about storage that surprises everybody once.

    A library IS knowledge, so the same operator imports it: ``m += lib.he``
    performs ``!(import! <m> (library lib_he))`` with this space as the
    target. An import is an effect, so it refuses to hide inside an atom
    batch or share a call with stored atoms.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if any(isinstance(atom, Library) for atom in atoms):
        if not all(isinstance(atom, Library) for atom in atoms):
            msg = (
                "imports and stores cannot share one add: a library "
                "handle performs an effect while atoms accumulate"
            )
            raise TypeError(msg)
        _spaces_scope_module._refuse_in_batch(space._space, "import")
        for handle in atoms:
            import_library(space, handle)
        return
    pending = _spaces_scope_module._ACTIVE_BATCHES.get().get(space._space)
    if pending is not None:
        # A Rules bundle rides the batch WHOLE, so the flush's re-entry
        # into this method sees its identity and publishes its evidence
        # only when the equations actually land; a discarded batch
        # therefore publishes nothing, which the eager spelling used to
        # get wrong.
        pending.extend(atoms)
        return
    if any(isinstance(atom, lazy('metta._declare.rules').Rules) for atom in atoms):
        # A bundle handed WHOLE keeps its identity: its equations stream
        # in place among the other atoms, and its construction evidence
        # publishes once they land, exactly as `m += bundle` publishes.
        # A SPLATTED bundle (`add(*bundle)`) was erased by the caller
        # before this method ran, which is the one spelling that cannot
        # carry the evidence.
        flattened: list[Any] = []
        for item in atoms:
            if isinstance(item, lazy('metta._declare.rules').Rules):
                flattened.extend(item)
            else:
                flattened.append(item)
        space.add(*flattened)
        for bundle in atoms:
            if isinstance(bundle, lazy('metta._declare.rules').Rules):
                _spaces_intents_module.register_rule_events(space, bundle)
        return
    wires = [_to_atom(atom).to_wire() for atom in atoms]
    if not wires:
        return
    if len(wires) == 1:
        _spaces_execution_module.run_void_write(space._rt, "metta_py_add", space._space, wires[0])
    else:
        _spaces_execution_module.run_void_write(space._rt, "metta_py_add_many", space._space, wires)
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch20_extending_the_engine/test_references.py::test_from_is_a_live_stored_row',),
    alias='from_',
    binding=_doors.Binding('metta_py_add', _doors.Wire.goal),
)
def from_(space: _root.Space, source: Any, map: Any = None) -> None:  # noqa: A002 -- map is the reference row's public argument
    """Reference a library or space through a stored ``(from source map)`` row.

        target.from_(metta.lib.string, metta.parse("(prefix str-)"))
        target.from_(home)

    A missing map uses this space's ``from-map`` pragma. Definitions run in
    their home and later additions follow the standing row. Removing the row
    withdraws its links. Loading follows this space's ``load`` pragma.
    """
    target = source.form if isinstance(source, Library) else _to_atom(source)
    fields = [Symbol("from"), target]
    if map is not None:
        fields.append(_to_atom(map))
    space.add(Expression(fields))

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_structures.py::test_matchindex_routes_and_removes', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_atoms_count_contains_remove_clear', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_delitem_removes_every_unifying_occurrence'),
    alias='remove',
    binding=_doors.Binding('metta_py_remove_many', _doors.Wire.goal),
)
def remove(space: _root.Space, atom: Any, *more: Any) -> bool | int:
    """Remove ONE unifying occurrence and say whether one was there,
    which is Python's own `list.remove` grain.

    Variadic like `add` and `transfer`: several atoms ride one engine
    crossing inside one transaction, and the answer counts the found,
    so the one-atom call still reads as the truth value it always
    was.

    `space -= atom` is this same grain without the report, the way
    `+=` is `add` without one: Python's in-place difference over a
    MULTISET, whose own Python spelling is `collections.Counter`,
    subtracts the multiplicity given rather than clearing the key.
    That is the only reading under which the operators are inverses,
    so `s += a; s -= a` leaves the space it found. `-=` classifies its
    operand exactly as `+=` does, so `-=` subtracts the same fact stream
    `+=` stores, one occurrence per element, in one
    transactional crossing.

    `del m[pattern]` is the draining form: it takes every
    unifying occurrence in one crossing and raises when nothing
    matched, as Python's `del` does, and MeTTa spells it `remove-atom`
    [source: engine/spaces/foreign.pl, remove_matching_atoms/2].
    MeTTa spells this method's grain `subtract-atom`. This is the one
    method that reports absence.

    A bare variable is the remove-everything reading a multiset space
    gives it, each atom leaving through its own proper path, equations
    and their compiled clauses included.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _spaces_scope_module._refuse_in_batch(space._space, "remove")
    if more:
        wires = [_to_atom(each).to_wire() for each in (atom, *more)]
        found = _spaces_execution_module.run_write(space._rt, "metta_py_remove_many", space._space, wires)
        lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)
        return int(found)
    pattern = _to_atom(atom)
    if isinstance(pattern, Variable):
        # The remove-everything reading, spelled as its own method rather
        # than reached by handing an unbound term to the one-occurrence
        # one. The engine's `subtract-atom` refuses that term precisely
        # because it would otherwise mean two opposite things in one head.
        removed = _spaces_execution_module.run_write(space._rt, "metta_py_remove_everything", space._space)
    else:
        removed = _spaces_execution_module.run_write(
            space._rt, "metta_py_remove", space._space, pattern.to_wire()
        )
    result = _atom_from_wire(removed)
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)
    return bool(getattr(result, "value", True))

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.integer,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_variadic_doors.py::test_transfer_moves_a_batch_atomically',),
)
def transfer(space: _root.Space, *atoms: Any, to: _root.Space) -> int:
    """Move ONE unifying occurrence of each atom into another space.

    Variadic and atomic: however many atoms ride the call, one engine
    transaction moves them in one crossing, so a mid-move failure
    rolls every side back and nothing is lost between the spaces. The
    answer counts the moved; an absent atom moves nothing and counts
    nothing, which is ``remove``'s own found-reporting grain, so the
    one-atom call still reads as a truth value. The longhand stays
    reachable: a :meth:`transaction` around ``remove`` and ``add``
    says the same thing one atom at a time. :meth:`take` is the
    WAITING kin for a pattern.
    """
    _spaces_scope_module._refuse_in_batch(space._space, "transfer")
    wires = [_to_atom(atom).to_wire() for atom in atoms]
    moved = _spaces_execution_module.run_write(
        space._rt, "metta_py_transfer", space._space, to._space, wires
    )
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)
    return int(moved)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    binding=_doors.Binding('metta_py_atoms', _doors.Wire.goal),
)
def atoms(space: _root.Space) -> list[Atom]:
    """Every stored atom in this space."""
    wires = space._rt.apply_must("metta_py_atoms", space._space)
    return [_atom_from_wire(w) for w in wires]

@_doors.door(
    kind=_doors.Kind.query,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_space_handle_peek_and_take_are_linda_verbs', 'extensions/python/tests/ch11_python_as_a_notation/test_library_fixes.py::test_peek_does_not_import_linda_into_the_waited_space', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings'),
)
def peek(
    space: _root.Space, pattern: Any, *, where: Any | None = None, deadline: float | None = None
) -> Atom:
    """Wait for one matching atom and leave it in this space.

    A finite deadline raises ``Timeout`` when no match arrives.

    `where` is match()'s guard on a blocking wait: a term over the
    pattern's variables, evaluated once a candidate binds them and
    required true, so "wait for a job whose priority is above five" is one
    call. Without it the guard had to live in the caller, as a wait and a
    re-wait around every candidate the guard rejected, and the deadline
    restarted each time round [measured 2026-08-31].
    """
    return _wait_for_atom(space, "peek-atom", pattern, where, deadline)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_space_handle_peek_and_take_are_linda_verbs', 'extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_the_linda_verbs_take_matchs_guard', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings'),
)
def take(
    space: _root.Space, pattern: Any, *, where: Any | None = None, deadline: float | None = None
) -> Atom:
    """Wait for and remove exactly one matching atom from this space.

    Competing takers cannot receive the same occurrence. A finite
    deadline raises ``TimeoutError`` when no match arrives. `where` is
    peek()'s guard, and it is checked BEFORE the removal, so an atom the
    guard rejects stays where it is for whoever does want it.
    """
    return _wait_for_atom(space, "take-atom", pattern, where, deadline)

def _wait_for_atom(
    space: _root.Space,
    operation: str,
    pattern: Any,
    where: Any | None,
    deadline: float | None,
) -> Atom:
    _spaces_cursor_module.require_deadline(deadline)
    caller = (
        space
        if space._space == _DEFAULT_SPACE
        else lazy('metta._faces.space').Space(_DEFAULT_SPACE, _runtime=space._rt)
    )
    caller.eval(
        Expression(
            [
                Symbol("import!"),
                caller,
                Expression([Symbol("library"), Symbol("lib_thread")]),
            ]
        )
    )
    arguments: list[Atom] = [space, _to_atom(pattern)]
    # The guarded pair carries its own NAME rather than another arity: a
    # guard and a timeout would both sit third, and nothing could tell
    # (peek-atom &s (job $x) 5) apart from a guard spelled 5.
    if where is None:
        operation = f"{operation.split('-', maxsplit=1)[0]}-atom"
    else:
        guard = _spaces_cursor_module.guard_atom(where)
        if guard is None:
            msg = f"where= is a term the engine evaluates per candidate, got {where!r}"
            raise TypeError(msg)
        arguments.append(guard)
        operation = (
            "space_await_where" if operation == "peek-atom" else "space_take_where"
        )
    if deadline is not None:
        arguments.append(Grounded(deadline))
    target = Expression([Symbol(operation), *arguments])
    answers = space.eval(target)
    if not answers:
        if deadline is None:
            msg = f"{operation} ended without an answer"
            raise EngineError(msg)
        msg = (
            f"no atom matching {pattern!r} arrived in {space._name} "
            f"within {deadline} seconds"
        )
        # metta.Timeout, the same class the coordination family raises,
        # so the guide's `except metta.Timeout` catches every deadline
        # miss; it subclasses TimeoutError, so the builtin clause still
        # works (agent A hit the split raising builtin TimeoutError here).
        raise Timeout(msg)
    _spaces_results_module.raise_error_answers(answers, space=space._space, target=target)
    if len(answers) != 1:
        msg = f"{operation} returned {len(answers)} answers, expected one"
        raise EngineError(msg)
    answer = answers[0]
    if not isinstance(answer, Atom):
        msg = f"{operation} returned {answer!r}, not an Atom"
        raise EngineError(msg)
    return answer

@overload
def cast(space: _root.Space, type_: _builtins.type[_CastT], /) -> _CastT: ...

@overload
def cast(space: _root.Space, type_: Atom | str, /) -> Any: ...

@overload
def cast(space: _root.Space, value: Any, type_: _builtins.type[_CastT], /) -> _CastT: ...

@overload
def cast(space: _root.Space, value: Any, type_: Atom | str, /) -> Any: ...

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch01_getting_started/test_api_types.py::test_cast_target_is_positional_only', 'extensions/python/tests/ch09_types/test_casting.py::test_arrow_typed_expressions_cast_structurally', 'extensions/python/tests/ch09_types/test_casting.py::test_atom_cast_delegates_to_the_ambient_space'),
)
def cast(space: _root.Space, value: Any, type_: Any = ..., /) -> Any:
    """Cast this space atom ambiently with one argument, or answer value
    narrowed by this space's type discipline with two arguments. The
    explicit form has the same acceptance a typed call compiles, ':'
    declarations here and &self in scope, protocol types included. A
    refusal raises metta.CastError naming the value's actual types.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if type_ is ...:
        return Handle.cast(space, value)
    return lazy('metta.convert').cast(space, value, type_)

@_doors.door(
    kind=_doors.Kind.lifecycle,
    answers=_doors.AnswersAs.space,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_a_copy_reproduces_the_space_it_copied',),
)
def copy(space: _root.Space) -> _root.Space:
    """This space's contents in a new anonymous space, cloned through
    one bulk write, so equations copy as equations and keep running:
    "a scratch space set up like production" is one line. The handle
    is ``space()``'s kind, so drop it, or use it as a context
    manager, to return the name. copy.copy(m) answers the same
    through the copy protocol. There is deliberately no __deepcopy__:
    stored Python objects keep their identity across the clone, the
    shallow reading, and a deep clone of a live engine handle has no
    meaning to promise.

    The contents are the space's OWN rows, the enumeration ``save()``
    persists: an origin row ``(from ...)`` copies, and the declarations
    and ``(@doc ...)`` rows that origin projected do not, because the
    clone's origin projects them again; copying them too gave every
    projected document a second, authored copy in the clone and a third
    in a copy of the copy, while a projected declaration was shadowed by
    its authored twin [source: engine/filereader/source_lifecycle.pl,
    metta_source_occurrence/4; tested:
    test_a_copy_leaves_projected_rows_to_the_origins_it_copies;
    commit=1bf85bb150defced36894b48722a861fee616609].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    lazy('metta.foreign').require_capability(space._space, "enumerate", "copy")
    # Enumerate the SOURCE before minting: a provider whose enumeration
    # fails then costs nothing, where minting first leaked an anonymous
    # clone on every such failure.
    wires = space._rt.apply_must("metta_py_source_atoms", space._space)
    atoms = [_atom_from_wire(w) for w in wires]
    # Specializer-generated equations add LAST, stably. Re-adding a base
    # equation invalidates the clone's specializations of that name, so
    # an enumeration that interleaves a base between two generated
    # clauses dropped the earlier one; with every base in first, each
    # generated equation compiles once and is adopted by the engine.
    atoms.sort(key=_copies_after_its_base)
    clone = space._new_space()
    if atoms:
        try:
            clone.add(*atoms)
        except BaseException:
            clone.drop()
            raise
    return clone

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.text,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_second_load_of_a_specialized_program_still_round_trips', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_specialized_program_saves_and_digests', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_digest_counts_duplicates'),
    binding=_doors.Binding('metta_py_digest', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.engine, 'extensions/python/tests/repository/test_door_refusals.py::test_digest_refuses_an_invalid_engine_reply'), _doors.Refusal(_doors.RefusalKind.value, 'extensions/python/tests/repository/test_door_refusals.py::test_digest_refuses_live_host_identity')),
)
def digest(space: _root.Space) -> str:
    """A sha256 hex digest of this space's content: every stored atom,
    equations included, canonicalized (variables numbered, multiset
    sorted) so the same atoms answer the same digest in any insertion
    order and in any process. Two spaces agree on digest() exactly
    when save() would write the same content. Live host objects have
    no cross-process identity and are refused, like save().
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    lazy('metta.foreign').require_capability(space._space, "enumerate", "digest")
    result = space._rt.apply_must("metta_py_digest", space._space)
    if not isinstance(result, list) or len(result) != 2:
        msg = f"metta_py_digest returned an invalid result: {result!r}"
        raise EngineError(msg)
    kind, value = result
    if kind == "object":
        atom = _atom_from_wire(value)
        msg = (
            f"{atom} carries a live Python object; it has no "
            f"cross-process identity to digest. Remove it, or digest "
            f"its data explicitly."
        )
        raise ValueError(
            msg
        )
    if kind == "symbol":
        _spaces_snapshot_module.raise_unsafe_text_atom(_atom_from_wire(value), "digest")
    if kind != "digest":
        msg = f"metta_py_digest returned an unknown result: {result!r}"
        raise EngineError(msg)
    return str(value)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.integer,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
)
def __len__(space: _root.Space) -> int:  # noqa: N807 -- the marked body preserves its Python protocol name
    """Read Space.__len__."""
    provider_length = lazy('metta.foreign')._provider_length(space._space)
    if provider_length is not None:
        return provider_length
    row = space._rt.once("metta_py_count(Space, N)", Space=space._space)
    return int(row["N"])

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.boolean,
    effect=_doors.EffectClass.pureStructural,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_space_identity_doors_follow_the_handle_lifetime',),
    state=_doors.State.any,
)
def __bool__(_space: _root.Space) -> bool:  # noqa: N807 -- the marked body preserves its Python protocol name
    """Always true: a space is a handle to a store, not a value that
    dwindles. Without this, bool() falls through to __len__ and an
    empty space is falsy, so `if space:` skips a perfectly good empty
    space, the bug class that made datetime stop treating midnight as
    false in 3.5. Existence is an ask: use
    ``bool(space.match(V.x))`` rather than ``bool(space)``.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return True

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.boolean,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
)
def __contains__(space: _root.Space, atom: Any) -> bool:  # noqa: N807 -- the marked body preserves its Python protocol name
    """Read Space.__contains__."""
    return space._rt.do("metta_py_contains", space._space, _to_atom(atom).to_wire())

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_atoms_count_contains_remove_clear', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_clear_removes_equations_too', 'extensions/python/tests/ch05_equations_and_evaluation/test_reload.py::test_a_cleared_space_forgets_what_a_file_put_in_it'),
    binding=_doors.Binding('metta_py_clear', _doors.Wire.goal),
)
def clear(space: _root.Space) -> None:
    """Remove everything stored here, compiled equations included."""
    _spaces_scope_module._refuse_in_batch(space._space, "clear")
    lazy('metta._declare.definitions').clear_definitions(space)
    _spaces_intents_module.clear(space)
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    context_inplace=True,
)
def __iadd__(space: _SpaceT, atom: Any) -> _SpaceT:  # noqa: N807 -- the marked body preserves its Python protocol name
    """add()'s operator spelling for one atom or one fact stream.

    ``m += (S.Edge, a, b)`` adds one fact. ``m += [(S.Edge, a, b),
    (S.Edge, b, c)]`` and a generator yielding those rows add two. A built
    Expression is always one atom even though it implements Sequence.
    Dataframes use ``iter_rows`` or ``itertuples(index=False)``. The
    explicit ``add(list_value)`` method remains available when a list itself
    is intended as one transparent expression.

    Relative ``S.admits(Type)``, ``S.capacity(n)``, and
    ``S.covers(effect)`` values are declared data: they install the same
    contract as the receiver methods and are not stored in this space.
    Explicit ``add(...)`` remains the raw storage method for those shapes.
    """
    if _install_relative_write_declaration(space, atom):
        return space
    if isinstance(atom, lazy('metta._declare.rules').Rules):
        # add() owns the bundle law now: equations land, then evidence
        # publishes, and a batch defers both together.
        space.add(atom)
        return space
    stream = _fact_stream(atom)
    if stream is None:
        space.add(atom)
    else:
        space.add(*stream)
    return space

def _install_relative_write_declaration(space: _root.Space, atom: Any) -> bool:
    """Install the three receiver-relative declarations recognized by ``+=``."""
    if (
        not isinstance(atom, Expression)
        or len(atom) != 2
        or not isinstance(atom.head, Symbol)
    ):
        return False
    argument = atom.children[1]
    if atom.head.name == "admits" and isinstance(argument, Symbol):
        _spaces_scope_module._refuse_in_batch(space._space, "declare")
        space.admits(argument.name)
        return True
    if atom.head.name == "covers" and isinstance(argument, Symbol):
        _spaces_scope_module._refuse_in_batch(space._space, "declare")
        space.covers(argument.name)
        return True
    if (
        atom.head.name == "capacity"
        and isinstance(argument, Grounded)
        and isinstance(argument.value, int)
        and not isinstance(argument.value, bool)
    ):
        _spaces_scope_module._refuse_in_batch(space._space, "declare")
        space.capacity(argument.value)
        return True
    return False

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    context_inplace=True,
)
def __isub__(space: _SpaceT, atom: Any) -> _SpaceT:  # noqa: N807 -- the marked body preserves its Python protocol name
    # -= is in-place DIFFERENCE over a MULTISET, and Python's own multiset
    # is collections.Counter, whose -= subtracts the multiplicity given
    # rather than clearing the key: Counter(a=3) -= Counter(a=1) leaves
    # a=2. `set -= {x}` looks total only because a set has no
    # multiplicity to subtract. So this takes ONE occurrence per operand
    # element, which is also the only reading under which += and -= are
    # inverses: `s += a; s -= a` has to leave the space it found, and a
    # drain takes copies the += never added. `del s[pattern]` is the
    # drain form and `remove()` the method that reports absence
    # [user ruling 2026-09-01, "consider python's Counter"].
    #
    # The operand reads by the SAME classification += writes by, so -=
    # subtracts the same fact stream += stores. Before that, a
    # tuple of rows quietly became one never-matching pattern and -=
    # "succeeded" over an unchanged space.
    """Read Space.__isub__."""
    _spaces_scope_module._refuse_in_batch(space._space, "remove")
    stream = _fact_stream(atom)
    if stream is None:
        # One element is already atomic, so it takes the single-item call.
        # The batch call opens a transaction for the atomicity a BATCH needs,
        # and a foreign provider that declares nothing about transactional
        # writes refuses one it did not ask for: the C-store example's
        # `store -= atom` failed that way the moment a single removal
        # borrowed the batch path [measured 2026-09-01].
        space._rt.apply_must(
            "metta_py_remove", space._space, _to_atom(atom).to_wire()
        )
    else:
        wires = [_to_atom(row).to_wire() for row in stream]
        space._rt.apply_must("metta_py_remove_many", space._space, wires)
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)
    return space

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:__ior__]'),),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    context_inplace=True,
)
def __ior__(space: _SpaceT, other: Any) -> _SpaceT:  # noqa: N807 -- the marked body preserves its Python protocol name
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
    an unregistered name is a KeyError rather than a parse.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(other, lazy('metta._faces.space').Space):
        merged: list[Any] = other.atoms()
    elif isinstance(other, Atom):
        merged = [other]
    elif isinstance(other, str):
        if other not in space.space_names():
            msg = (
                f"{other!r} is not a registered space name; "
                f"space_names() lists them. To add atoms, pass an "
                f"iterable: m |= [{other!r}]"
            )
            raise KeyError(
                msg
            )
        merged = lazy('metta._faces.space').Space(other, _runtime=space._rt).atoms()
    elif isinstance(other, (bytes, bytearray, _abc.Mapping)):
        msg = (
            f"|= does not read a {type(other).__name__}: add() would "
            f"lift it into one atom, and iterating it here would read "
            f"the same operand a second way. Use m.add(x) for one "
            f"atom, or spell the elements: m |= list-of-atoms"
        )
        raise TypeError(
            msg
        )
    elif isinstance(other, _abc.Iterable):
        merged = list(other)
    else:
        msg = (
            f"|= merges a space, a registered space name, or an "
            f"iterable of atoms; {type(other).__name__} is none of "
            f"those"
        )
        raise TypeError(
            msg
        )
    space.add(*merged)
    return space

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.stream,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space_container_protocol.py::test_native_iteration_snapshots_before_mutation',),
)
def __iter__(space: _root.Space):  # noqa: N807 -- the marked body preserves its Python protocol name
    """Iterate one assembly-order snapshot of the stored atoms.

    A native or inherited-native space materializes its readable chain
    when ``iter(space)`` is called, so later additions and removals do not
    alter that iterator. A Python-backed space likewise materializes its
    provider's ``atoms()`` result before returning the iterator; the
    provider owns and must document how concurrent mutation behaves while
    that one enumeration itself is being produced.
    """
    return iter(space.atoms())

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.rows,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:__getitem__]'),),
)
def __getitem__(space: _root.Space, i: Any) -> _root.Rows:  # noqa: N807 -- the marked body preserves its Python protocol name
    """Subscription is query. A tuple headed by an atom is one built
    expression pattern; a tuple of complete expression patterns is a join:

        m[(S.Parent, V.x, S.Bob)]
        m[S.edge(V.a, V.b), S.edge(V.b, V.c)]

    Python hands both spellings to ``__getitem__`` as a tuple, so shape is
    the visible classifier. A mixed tuple beginning with a complete
    pattern and followed by a bare atom can only be the tuple mistake; it
    raises and names the one-pattern and join spellings instead of
    silently asking an impossible bare-atom conjunct.

    A str key parses first, matching match()'s tolerance. A slice is
    refused: a slice of a space has no one meaning, and the bounded
    readings have their own methods, match(limit=) for a bounded answer
    set and stream() for rows pulled until you have seen enough.
    """  # noqa: D205, D415  -- the API contract is one continuous invariant, not summary-and-body prose; the first line deliberately introduces the indented example that follows
    pattern = i
    if isinstance(pattern, slice):
        msg = (
            "a space cannot be sliced; match(limit=n) bounds the "
            "answer set, stream() pulls rows until you stop"
        )
        raise TypeError(
            msg
        )
    if isinstance(pattern, tuple):
        complete = (Expression, tuple)
        if not pattern or not isinstance(pattern[0], complete):
            return space.match(pattern)
        if not all(isinstance(part, complete) for part in pattern):
            msg = (
                "a subscript is one pattern as space[(head, ...)] or a "
                "join of complete patterns as space[p1, p2] (equivalently "
                "space.match(p1, p2)); a bare atom cannot be a join conjunct"
            )
            raise TypeError(msg)
        return space.match(*pattern)
    return space.match(pattern)

@_doors.door(
    kind=_doors.Kind.write,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.context),
    evidence=('extensions/python/tests/repository/test_door_rows.py::test_generated_space_protocols_preserve_storage_and_identity',),
)
def __delitem__(space: _root.Space, pattern: Any) -> None:  # noqa: N807 -- the marked body preserves its Python protocol name
    """Del m[pattern] removes every unifying occurrence, the bulk
    spelling of remove()'s multiset subtraction: m[pattern] is a
    query answering many rows, so deleting it deletes them all, the
    way DELETE WHERE does. Nothing unifying raises KeyError, as
    del d[k] does on a missing key; remove() is the method that
    reports absence as False instead.

    It asks the engine's own drain, so the whole pattern costs ONE
    crossing rather than one per removed atom.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _spaces_scope_module._refuse_in_batch(space._space, "remove")
    existed = _spaces_execution_module.run_write(
        space._rt, "metta_py_drain", space._space, _to_atom(pattern).to_wire()
    )
    lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)
    if not bool(getattr(_atom_from_wire(existed), "value", True)):
        raise KeyError(pattern)

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
