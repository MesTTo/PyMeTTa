"""Purpose: prove the public five-rank operation-effect lattice.

Assumes:
  - the engine catalog is the authority for ``EffectClass`` member order.
Guarantees:
  - unclassified registration refuses before publishing any operation fact
    [tested: test_unclassified_operation_refuses_with_all_five_effect_remedies;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - declaration-route classes must be symbols, so reflection cannot carry a
    grounded impostor [tested: test_effect_declaration_requires_a_symbol_class;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - every rank registers and a composed definition reflects the strongest
    callee [tested: test_every_effect_rank_registers_and_reflects,
    test_a_definition_joins_every_called_operations_effect,
    test_stacked_clauses_join_again_in_definition_reflection,
    test_definition_match_is_a_nondeterministic_read; commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - Python registration publishes the same canonical row consumed by
    ``metta_contract_fact/1`` [tested:
    test_python_registered_effect_is_an_engine_contract_fact; commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
"""

import itertools
import time

import pytest

from metta import parse
from metta.ops import registered
from metta.vocabularies import EffectClass


def _representative_operations():
    """Return one operation whose behavior inhabits each declared rank."""
    lookup = {"known": "value"}
    writes = []

    def pure(value):
        return value

    def read(value):
        return lookup.get(value, value)

    def choices(value):
        yield value
        yield value

    def write(value):
        writes.append(value)
        return value

    def oracle(_value):
        return time.monotonic_ns()

    return {
        EffectClass.pureStructural: pure,
        EffectClass.readOnlyLookup: read,
        EffectClass.nondeterministicReadOnly: choices,
        EffectClass.writesState: write,
        EffectClass.oracleIO: oracle,
    }


def test_effect_class_is_the_public_five_rank_join_lattice():
    """The engine's declared order is the Python order and comparison order."""
    assert [effect.value for effect in EffectClass] == [
        "pureStructural",
        "readOnlyLookup",
        "nondeterministicReadOnly",
        "writesState",
        "oracleIO",
    ]
    assert [effect.rank for effect in EffectClass] == list(range(5))
    assert all(left < right for left, right in itertools.combinations(EffectClass, 2))


def test_effect_join_obeys_the_lattice_laws():
    """Join is max rank, with structural purity as the empty-plan identity."""
    for left, right in itertools.product(EffectClass, repeat=2):
        assert left.join(right) is right.join(left)
        assert left.join(left) is left
        assert left.join(right).rank == max(left.rank, right.rank)
        assert EffectClass.pureStructural.join(left) is left
    for left, middle, right in itertools.product(EffectClass, repeat=3):
        assert left.join(middle).join(right) is left.join(middle.join(right))
    assert EffectClass.compose([]) is EffectClass.pureStructural


def test_unclassified_operation_refuses_with_all_five_effect_remedies(metta):
    """Missing metadata fails before registry or engine reflection mutation."""
    name = "effect-unclassified"
    with pytest.raises(TypeError) as refused:
        metta.op(lambda value: value, name=name)
    message = str(refused.value)
    for effect in EffectClass:
        assert f"EffectClass.{effect.value}" in message
    assert name not in registered()
    assert not metta._at("&metta").match(parse(f"(op {name} $arity $kind)"))
    assert not metta._at("&metta").match(parse(f"(effect {name} $effect)"))


def test_every_effect_rank_registers_and_reflects(metta):
    """Each canonical class survives the Python and catalog reflection doors."""
    names = []
    operations = _representative_operations()
    try:
        for effect in EffectClass:
            name = f"effect-rank-{effect.rank}"
            names.append(name)
            metta.op(operations[effect], name=name, effect=effect)
            operation = registered()[name]
            assert operation.effect is effect
            assert operation.pure is (effect is EffectClass.pureStructural)
            rows = metta._at("&metta").match(parse(f"(effect {name} $e)"))
            assert [str(row.e) for row in rows] == [effect.value]
            explanation = metta.run(f"!(explain ({name} probe))")
            reflected = {
                str(item.children[0]): item
                for item in explanation[0][0].children
            }
            assert str(reflected["effect"].children[1]) == effect.value
    finally:
        for name in names:
            if name in registered():
                metta.unregister_op(name)


def test_composed_operation_plan_uses_its_strongest_member(metta):
    """Operation reflection supplies the inputs to the public plan composer."""
    names = ["effect-plan-read", "effect-plan-write", "effect-plan-io"]
    effects = [
        EffectClass.readOnlyLookup,
        EffectClass.writesState,
        EffectClass.oracleIO,
    ]
    operations = _representative_operations()
    try:
        for name, effect in zip(names, effects, strict=True):
            metta.op(operations[effect], name=name, effect=effect)
        plan = [registered()[name] for name in names]
        assert EffectClass.compose(operation.effect for operation in plan) is EffectClass.oracleIO
    finally:
        for name in names:
            if name in registered():
                metta.unregister_op(name)


def test_a_definition_joins_every_called_operations_effect(metta):
    """The compiled-plan reflection is the strongest effect of its calls."""
    lookup = {"known": "value"}
    writes = []

    def effect_join_read(value):
        return lookup.get(value, value)

    def effect_join_write(value):
        writes.append(value)
        return value

    metta.op(
        effect_join_read,
        name="effect_join_read",
        effect=EffectClass.readOnlyLookup,
    )
    metta.op(
        effect_join_write,
        name="effect_join_write",
        effect=EffectClass.writesState,
    )
    try:
        @metta.define
        def effect_join_definition(value):
            looked_up = effect_join_read(value)
            return effect_join_write(looked_up)

        assert effect_join_definition.effect is EffectClass.writesState
        rows = metta._at("&metta").match(
            parse("(effect effect-join-definition $effect)")
        )
        assert [str(row.effect) for row in rows] == ["writesState"]
    finally:
        metta.unregister_op("effect_join_read")
        metta.unregister_op("effect_join_write")


def test_stacked_clauses_join_again_in_definition_reflection(metta):
    """The reflected definition plan joins effects across all live clauses."""
    lookup = {"known": "value"}
    writes = []

    def effect_stack_read(value):
        return lookup.get(value, value)

    def effect_stack_write(value):
        writes.append(value)
        return value

    metta.op(
        effect_stack_read,
        name="effect_stack_read",
        effect=EffectClass.readOnlyLookup,
    )
    metta.op(
        effect_stack_write,
        name="effect_stack_write",
        effect=EffectClass.writesState,
    )
    try:
        @metta.define(name="effect-stack")
        def effect_stack_read_clause(value=0):  # noqa: ARG001  -- the literal default is the clause-head pattern
            return effect_stack_read(0)

        @metta.define(name="effect-stack")
        def effect_stack_write_clause(value=1):  # noqa: ARG001  -- the literal default is the clause-head pattern
            return effect_stack_write(1)

        assert effect_stack_read_clause.effect is EffectClass.readOnlyLookup
        assert effect_stack_write_clause.effect is EffectClass.writesState
        rows = metta._at("&metta").match(parse("(effect effect-stack $effect)"))
        assert [str(row.effect) for row in rows] == ["writesState"]
    finally:
        metta.unregister_op("effect_stack_read")
        metta.unregister_op("effect_stack_write")


def test_compiler_recognized_python_calls_remain_structural(metta):
    """A structural lowering contributes no effect beyond its arguments."""
    @metta.define
    def effect_structural_length(values):
        return len(values)

    assert effect_structural_length.effect is EffectClass.pureStructural
    rows = metta._at("&metta").match(
        parse("(effect effect-structural-length $effect)")
    )
    assert [str(row.effect) for row in rows] == ["pureStructural"]


def test_definition_match_is_a_nondeterministic_read(metta):
    """Space matching reflects a branching read, never a state write."""
    metta.add(parse("(effect_match_fact 7)"))

    @metta.define
    def effect_match_definition():
        return match(effect_match_fact(value), value)  # noqa: F821

    assert (
        effect_match_definition.effect
        is EffectClass.nondeterministicReadOnly
    )
    rows = metta._at("&metta").match(
        parse("(effect effect-match-definition $effect)")
    )
    assert [str(row.effect) for row in rows] == ["nondeterministicReadOnly"]
    assert metta.run("!(effect-match-definition)") == [[7]]


@pytest.mark.parametrize(
    ("legacy", "canonical"),
    [
        ("immutable", EffectClass.pureStructural),
        ("stable", EffectClass.readOnlyLookup),
        ("volatile", EffectClass.oracleIO),
    ],
)
@pytest.mark.parametrize("route", ("keyword", "declaration"))
def test_legacy_effect_names_normalize_to_canonical_classes(
    metta, legacy, canonical, route
):
    """Both compatibility inputs normalize the retired volatility trio."""
    name = f"effect-legacy-{route}-{legacy}"
    metadata = (
        {"effect": legacy}
        if route == "keyword"
        else {"declarations": [parse(f"(effect {name} {legacy})")]}
    )
    metta.op(
        _representative_operations()[canonical],
        name=name,
        **metadata,
    )
    try:
        assert registered()[name].effect is canonical
        rows = metta._at("&metta").match(parse(f"(effect {name} $effect)"))
        assert [str(row.effect) for row in rows] == [canonical.value]
    finally:
        metta.unregister_op(name)


def test_effect_declaration_requires_a_symbol_class(metta):
    """A declaration cannot smuggle a grounded value into the effect row."""
    name = "effect-grounded-class"
    declaration = parse(f'(effect {name} "pureStructural")')
    with pytest.raises(TypeError, match="must name its class as a symbol"):
        metta.op(lambda value: value, name=name, declarations=[declaration])
    assert name not in registered()


def test_python_registered_effect_is_an_engine_contract_fact(metta):
    """The Python catalog atom is directly visible to the engine contract seam."""
    name = "effect-engine-contract"
    metta.op(
        _representative_operations()[EffectClass.readOnlyLookup],
        name=name,
        effect=EffectClass.readOnlyLookup,
    )
    try:
        row = metta.runtime.once(
            "metta_contract_fact([effect, Name, Effect])",
            Name=name,
        )
        assert str(row["Effect"]) == "readOnlyLookup"
    finally:
        metta.unregister_op(name)
