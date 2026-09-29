"""Purpose: keep algebra declarations inside their named or pooled space life.

Guarantees:
  - dropping a space removes its algebra before the name can be reused
    [tested: test_drop_retires_algebra_before_redeclaration; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - transaction rollback restores the exact algebra mirror preimage, including
    nested declarations [tested: test_rollback_releases_an_algebra_mirror,
    test_rollback_restores_a_replaced_algebra_mirror; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - the operations an algebra makes from callables belong to its declaring
    space: one name in two spaces keeps each space's callables, the space's
    drop and a refused declaration's rollback release them, effect= classifies
    them, and a row the engine refuses is an AlgebraDeclarationError, at the
    space's door and the module call alike [tested 2026-09-29T05:09:00+10:00:
    test_one_algebra_name_in_two_spaces_keeps_each_space_s_operations,
    test_a_space_s_drop_and_a_refusal_release_the_operations_its_algebras_made,
    test_effect_classifies_the_operations_an_algebra_makes,
    test_a_declaration_the_engine_refuses_is_an_algebra_declaration_error]
  - the engine's key alone refuses a name the space already declares, as the
    row lands or as the transaction commits: the door answers
    algebra_already_declared(<name>) with the IntegrityError as its cause,
    whose key is the row's (name space) Expression, four racing workers
    leave one row and the winner's operations, and a commit the caller owns
    meets the IntegrityError itself [tested
    2026-09-29T06:01:28+10:00:
    test_a_name_the_space_declares_is_refused_by_the_engine_s_key,
    test_racing_declarations_of_one_name_leave_one_row_and_refuse_the_rest,
    test_a_declaration_refused_at_the_caller_s_commit_reaches_the_caller_as_the_integrity_error]
"""
import importlib
import operator
import threading
import uuid
from contextlib import ExitStack

import pytest

from metta import Expression, S, V, registered
from metta._errors.errors import EngineError, IntegrityError
from metta.vocabularies import EffectClass


@pytest.mark.parametrize("named", [True, False])
def test_drop_retires_algebra_before_redeclaration(metta, named):
    """Named and pooled space names begin their next algebra life empty."""
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        first = metta._at("&algebra-lifecycle") if named else metta._new_space()
        cleanup.callback(first.drop)
        name = first.name
        first.algebra("local-product", combine="+", extend="*", zero=0, one=1)
        first.annotations("local-product")
        assert algebra.require(first, "local-product").combine == "+"
        first.drop()
        # metta_py_pool_space appends behind names released by earlier tests.
        attempts = 1 if named else metta.runtime.must(
            "aggregate_all(count, metta_py_free_space(_), N)"
        )["N"]
        second = None
        for _ in range(attempts):
            candidate = metta._at(name) if named else metta._new_space()
            cleanup.callback(candidate.drop)
            if candidate.name == name:
                second = candidate
                break
        assert second is not None
        with pytest.raises(algebra.AlgebraDeclarationError, match="algebra_not_declared"):
            algebra.require(second, "local-product")
        assert not second.runtime.once(
            "metta_catalog_row([annotations, Ctx|_])", Ctx=second.name
        )
        second.algebra("local-product", combine="max", extend="*", zero=0, one=1)
        second.add_tagged_fact(2, S.input(S.a))
        second.add_tagged_rule(3, S.output(S.a), S.input(S.a))
        assert second.match(S.output(S.a), under="local-product").one().annotation == 6
        assert algebra.require(second, "local-product").combine == "max"


@pytest.mark.parametrize("nested", [False, True])
def test_rollback_releases_an_algebra_mirror(metta, nested):
    """An aborted transaction retains neither catalog row nor Python mirror."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        key = algebra._key(space, str(space.name), "rolled-back-carrier")

        def declare():
            space.algebra("rolled-back-carrier", combine="max", extend="*",
                          zero=0, one=1, type=int)

        def abort():
            if nested:
                space.transaction(declare)
            else:
                declare()
            msg = "abort algebra declaration"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort algebra declaration"):
            space.transaction(abort)
        assert not space.runtime.once(
            "metta_catalog_row([algebra,'rolled-back-carrier',_,_,_,_,_,_,_,Ctx])",
            Ctx=space.name,
        )
        assert key not in algebra._REGISTRY


def test_rollback_restores_a_replaced_algebra_mirror(metta):
    """A replacement rollback restores the original declaration object."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        original_row = space.algebra("replaced-carrier", combine="max", extend="*",
                                     zero=0, one=1, type=int)
        original = algebra.require(space, "replaced-carrier")
        key = algebra._key(space, str(space.name), "replaced-carrier")

        def replace_and_abort():
            space._at("&metta").remove(original_row)
            space.algebra("replaced-carrier", combine="+", extend="*",
                          zero=0.0, one=1.0, type=float)
            msg = "abort algebra replacement"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort algebra replacement"):
            space.transaction(replace_and_abort)
        assert algebra._REGISTRY[key][1] is original
        assert algebra.require(space, "replaced-carrier") is original
        assert original.type is int


def _declare(door, space, name, **roles):
    """Declare through the door under test: the space's own, or the module call inside `with space:`."""
    algebra = importlib.import_module("metta.algebra")
    if door == "space":
        return space.algebra(name, **roles)
    with space:
        return algebra(name, **roles)


def _fold(space, name):
    """The named algebra's combine over the space's two derivations of (p), read back through prov."""
    algebra = importlib.import_module("metta.algebra")
    declared = algebra.resolve(space, name)
    return [answer.under(declared).annotation for answer in space.match(S.p(), under=algebra.prov)]


@pytest.mark.parametrize("door", ["space", "module"])
def test_one_algebra_name_in_two_spaces_keeps_each_space_s_operations(metta, door):
    """A second space declaring a name leaves the first space's callables where they are.

    An operation an algebra makes from a callable is named for its declaring
    space: the process registers every operation into one module every space
    inherits, and `<algebra>-<role>` alone let the second space's `max`
    replace the first space's `+` under the first space's row.
    """
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        keep, other = (metta._at(f"&algebra-{door}-{uuid.uuid4().hex[:8]}") for _ in range(2))
        for space in (keep, other):
            cleanup.callback(space.drop)
            space.add(algebra.tagged_fact(0.5, S.p()), algebra.tagged_fact(0.25, S.p()))
        _declare(door, keep, "shared-name", combine=operator.add, extend=operator.mul, zero=0.0, one=1.0)
        assert _fold(keep, "shared-name") == [0.75]
        _declare(door, other, "shared-name", combine=max, extend=operator.mul, zero=0.0, one=1.0)
        assert _fold(other, "shared-name") == [0.5]
        assert _fold(keep, "shared-name") == [0.75]
        qualifier = str(keep.name).removeprefix("&")
        assert algebra.resolve(keep, "shared-name").combine == f"{qualifier}.shared-name-combine-1"


@pytest.mark.parametrize("door", ["space", "module"])
def test_a_space_s_drop_and_a_refusal_release_the_operations_its_algebras_made(metta, door):
    """The operations made from callables live as long as the declaration that holds them."""
    algebra = importlib.import_module("metta.algebra")
    space = metta._at(f"&owned-{door}-{uuid.uuid4().hex[:8]}")
    qualifier = str(space.name).removeprefix("&")
    try:
        with pytest.raises(algebra.AlgebraDeclarationError, match="algebra_value_outside_carrier"):
            _declare(door, space, "refused", combine=max, extend=operator.mul, zero="bad", one=1, type=int)
        assert not [name for name in registered() if name.startswith(f"{qualifier}.")]
        _declare(door, space, "owned", combine=operator.add, extend=operator.mul, zero=0, one=1,
                 negate=lambda value: 1 - value)
        declared = algebra.require(space, "owned")
        owned = {declared.combine, declared.extend, declared.negation}
        # Each attempt takes the space's next ordinals, the refused one's too.
        assert sorted(owned) == [f"{qualifier}.owned-{role}" for role in ("combine-3", "extend-4", "negate-5")]
        assert owned <= set(registered())
    finally:
        space.drop()
    assert not owned & set(registered())


def test_effect_classifies_the_operations_an_algebra_makes(metta):
    """An algebra's author says what its operations read; the default stays arithmetic."""
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        space = metta._at(f"&effect-{uuid.uuid4().hex[:8]}")
        cleanup.callback(space.drop)
        space.algebra("reads-binding", combine=operator.add, extend=operator.mul, zero=0, one=1,
                      effect=EffectClass.readOnlyLookup)
        space.algebra("arithmetic", combine=operator.add, extend=operator.mul, zero=0, one=1)
        effects = {
            name: {registered()[getattr(algebra.require(space, name), role)].effect for role in ("combine", "extend")}
            for name in ("reads-binding", "arithmetic")
        }
        assert effects == {"reads-binding": {EffectClass.readOnlyLookup}, "arithmetic": {EffectClass.pureStructural}}
        with pytest.raises(TypeError, match="effect="):
            space.algebra("named-only", combine="+", extend="*", zero=0, one=1, effect=EffectClass.readOnlyLookup)


@pytest.mark.parametrize("door", ["space", "module"])
def test_a_declaration_the_engine_refuses_is_an_algebra_declaration_error(metta, door):
    """Whatever refuses the row, a declaration refused is an AlgebraDeclarationError."""
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        space = metta._at(f"&refused-{door}-{uuid.uuid4().hex[:8]}")
        cleanup.callback(space.drop)
        with pytest.raises(algebra.AlgebraDeclarationError, match="ZeroDivisionError") as refused:
            _declare(door, space, "raising", combine=lambda left, right: (left + right) / 0, extend=operator.mul,
                     zero=0, one=1, carrier=(0, 1), laws=("combine-associative",))
        assert isinstance(refused.value.__cause__, EngineError)


def _algebra_key(key, name, space):
    """Whether an IntegrityError's key is an algebra row's: an Expression of its name, then its space."""
    return isinstance(key, Expression) and key.children[0] == S[name] and str(key) == f"({name} {space.name})"


@pytest.mark.parametrize("door", ["space", "module"])
def test_a_name_the_space_declares_is_refused_by_the_engine_s_key(metta, door):
    """A second declaration of one name in one space is refused by the row's key and leaves the first standing."""
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        space = metta._at(f"&twice-{door}-{uuid.uuid4().hex[:8]}")
        cleanup.callback(space.drop)
        qualifier = str(space.name).removeprefix("&")
        _declare(door, space, "twice", combine=operator.add, extend=operator.mul, zero=0, one=1)
        with pytest.raises(algebra.AlgebraDeclarationError) as refused:
            _declare(door, space, "twice", combine=max, extend=operator.mul, zero=0, one=1)
        assert str(refused.value) == "algebra_already_declared(twice)"
        taken = refused.value.__cause__
        assert isinstance(taken, IntegrityError)
        assert taken.head == "algebra"
        assert _algebra_key(taken.key, "twice", space)
        first = [f"{qualifier}.twice-combine-1", f"{qualifier}.twice-extend-2"]
        declared = algebra.require(space, "twice")
        assert [declared.combine, declared.extend] == first
        # The refused attempt made twice-combine-3 and twice-extend-4 and rolled them back.
        assert sorted(name for name in registered() if name.startswith(f"{qualifier}.")) == first


def test_racing_declarations_of_one_name_leave_one_row_and_refuse_the_rest(metta, monkeypatch):
    """Pool workers declaring one name at once: one declares, every other is refused by the key.

    Each worker is held after the engine admits its row into its own
    transaction and before that transaction commits, until all four are
    there, so every row passes the check as it lands, in a view holding no
    other, and the key decides at the commits: the interleaving that let
    several declarations each publish a row (the MeTTa-PC integration's
    ledger measured three rows from four workers).
    """
    algebra = importlib.import_module("metta.algebra")
    everyone = threading.Barrier(4, timeout=10)
    admitted = algebra._record_algebra_undo

    def held(key):
        everyone.wait()
        return admitted(key)

    with ExitStack() as cleanup:
        shared = metta._at(f"&race-{uuid.uuid4().hex[:8]}")
        cleanup.callback(shared.drop)
        # Registered after the drop so it runs first: the drop's own mirror
        # release goes through the held hook, which would wait for workers.
        monkeypatch.setattr(algebra, "_record_algebra_undo", held)
        cleanup.callback(monkeypatch.undo)
        qualifier = str(shared.name).removeprefix("&")

        def declare(_worker: int) -> tuple[object, ...]:
            try:
                shared.algebra("race", combine=operator.add, extend=operator.mul, zero=0, one=1)
            except algebra.AlgebraDeclarationError as refusal:
                taken = refusal.__cause__
                return str(refusal), type(taken).__name__, getattr(taken, "head", None), getattr(taken, "key", None)
            return ("declared",)

        with shared.pool(workers=4) as pool:
            outcomes = list(pool.map(declare, range(4)))
        monkeypatch.undo()
        refused = [outcome for outcome in outcomes if outcome[0] != "declared"]
        assert len(outcomes) - len(refused) == 1
        assert [outcome[:3] for outcome in refused] == [("algebra_already_declared(race)", "IntegrityError", "algebra")] * 3
        assert all(_algebra_key(outcome[3], "race", shared) for outcome in refused)
        rows = metta._at("&metta").match(S.algebra(S.race, *(V[f"slot{index}"] for index in range(8))))
        assert len([row for row in rows if str(row["slot7"]) == str(shared.name)]) == 1
        # Each attempt made its own operations; the three refused rolled theirs
        # back, and the name resolves to the operations of the row that stands.
        owned = {name for name in registered() if name.startswith(f"{qualifier}.race-")}
        declared = algebra.require(shared, "race")
        assert len(owned) == 2
        assert {declared.combine, declared.extend} == owned


def test_a_declaration_refused_at_the_caller_s_commit_reaches_the_caller_as_the_integrity_error(metta):
    """Inside a transaction of the caller's own, the key's answer at the commit is the caller's to meet.

    Two workers each declare one name inside their own transaction and wait
    for each other before committing, so each row lands in a view holding
    neither and the key decides at the commits, outside the declaration door.
    """
    both_written = threading.Barrier(2, timeout=10)
    with ExitStack() as cleanup:
        shared = metta._at(f"&commit-race-{uuid.uuid4().hex[:8]}")
        cleanup.callback(shared.drop)

        def declare_then_commit(_worker: int) -> tuple[object, ...]:
            def body() -> None:
                shared.algebra("contested", combine="+", extend="*", zero=0, one=1)
                both_written.wait()

            try:
                shared.transaction(body)
            except IntegrityError as taken:
                return taken.head, taken.key
            return ("committed",)

        with shared.pool(workers=2) as pool:
            outcomes = list(pool.map(declare_then_commit, range(2)))
        refused = [outcome for outcome in outcomes if outcome != ("committed",)]
        assert len(refused) == 1
        assert refused[0][0] == "algebra"
        assert _algebra_key(refused[0][1], "contested", shared)
