"""Purpose: verify class field aliases and the lifetime of generated host calls.

Guarantees:
  - class fields preserve Python container identity, adopt native values once,
    and roll back replacement through the existing engine transaction [tested:
    sh extensions/python/test.sh tests/ch09_types/test_class_field_values.py -n 0;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
"""

from dataclasses import dataclass, field
from typing import Annotated, Any

import annotated_types as at
import pytest

from metta import Grounded, MeTTa, S, Space, convert
from metta._declare.classes import declaration
from metta._declare.operations import registered
from metta._errors.errors import EngineError


@pytest.mark.parametrize("base", [object, Space])
def test_container_fields_keep_python_aliases(base):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        @context.self.define
        @dataclass
        class ClassFieldAliases(base):
            items: list[int] = field(default_factory=list)
            mapping: dict[str, int] = field(default_factory=dict)
            members: set[int] = field(default_factory=set)
            nested: tuple[list[int], ...] = ()
            arbitrary: Any = None

        left, right = ClassFieldAliases(), ClassFieldAliases()
        left.items.append(1)
        left.mapping["a"] = 2
        left.members.add(3)
        assert (left.items, left.mapping, left.members) == ([1], {"a": 2}, {3})
        assert (right.items, right.mapping, right.members) == ([], {}, set())

        shared = [4]
        left.items = right.items = shared
        left.nested = (shared,)
        left.arbitrary = shared
        assert left.items is right.items is left.nested[0] is left.arbitrary is shared
        shared.append(5)
        assert left.items == [4, 5]
        old = left.items
        left.items = [6]
        old.append(7)
        assert left.items == [6]
        assert right.items == [4, 5, 7]
        receiver = convert.project(right).atom
        native = context.self.eval(S["ClassFieldAliases-items"](receiver))
        assert len(native) == 1 and isinstance(native[0], Grounded)
        assert native[0].value is shared


def test_native_container_fields_are_adopted_once():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClassNativeContainers:
            items: list[int]
            mapping: dict[str, int]
            members: set[int]
            nested: tuple[list[int], ...]

        receiver = m.run('!(make-ClassNativeContainers (1 2) ((entry "a" 3)) (4 5) ((6)))')[0][0]
        value = convert.build(receiver, ClassNativeContainers)
        assert (value.items, value.mapping, value.members, value.nested) == ([1, 2], {"a": 3}, {4, 5}, ([6],))
        value.items.append(7)
        value.mapping["b"] = 8
        value.members.add(9)
        value.nested[0].append(10)
        again = convert.build(receiver, ClassNativeContainers)
        assert (again.items, again.mapping, again.members, again.nested) == ([1, 2, 7], {"a": 3, "b": 8}, {4, 5, 9}, ([6, 10],))
        old = value.items
        assert m.run(f'!(ClassNativeContainers-items! {receiver} (11 12))') == [[True]]
        old.append(13)
        assert value.items == [11, 12]
        plan = declaration(ClassNativeContainers)
        operation = registered()[plan.field_adopter.name]
        assert operation.effect.value == "oracleIO"


@pytest.mark.parametrize("base", [object, Space])
def test_field_replacement_rolls_back_but_external_mutation_is_a_host_effect(base):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClassFieldRollback(base):
            items: list[int]

        supplied = [1]
        value = ClassFieldRollback(supplied)
        assert value.items is supplied

        def rejected():
            value.items.append(2)
            value.items = [3]
            msg = "discard replacement"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="discard replacement"):
            m.transaction(rejected)
        assert value.items is supplied
        assert value.items == [1, 2]


def test_class_generated_operations_retire_and_declaration_rollback_retries():  # noqa: D103 -- pytest discovers this test; its name states the contract
    names = []
    with MeTTa() as context:
        m = context.self

        @dataclass
        class ClassOwnedFactories:
            items: list[int] = field(default_factory=list)
            answer: int = field(default_factory=lambda: 42)

        def rejected():
            m.define(ClassOwnedFactories)
            msg = "discard declaration"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="discard declaration"):
            m.transaction(rejected)
        assert not any("ClassOwnedFactories" in name for name in registered())
        m.define(ClassOwnedFactories)
        assert ClassOwnedFactories().answer == 42
        names = list(declaration(ClassOwnedFactories).operations)
        assert names and all(name in registered() for name in names)
    assert all(name not in registered() for name in names)


def test_retiring_a_class_preserves_a_replacement_host_implementation():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClassReplacedFactory:
            answer: int = field(default_factory=lambda: 42)

        plan = declaration(ClassReplacedFactory)
        name = next(iter(plan.operations))
        m.op(lambda: 7, name=name, effect="oracleIO", arities=[0])
        try:
            plan.space.drop()
            assert m.eval(S[name]()) == [7]
        finally:
            m.unregister_op(name)


@pytest.mark.parametrize("base", [object, Space])
def test_container_refinements_guard_native_and_host_field_writes(base):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClassRefinedContainer(base):
            items: Annotated[list[int] | tuple[int, ...], at.MinLen(2)]

        retained = [1, 2]
        value = ClassRefinedContainer(retained)
        receiver = convert.project(value).atom
        with pytest.raises(EngineError, match="BadArgValue"):
            value.items = [3]
        assert value.items is retained
        with pytest.raises(EngineError, match="BadArgValue"):
            value.items = (3,)
        assert value.items is retained
        refused = m.run(f"!(ClassRefinedContainer-items! {receiver} (3))")[0]
        assert len(refused) == 1 and refused[0].head == S.Error
        assert "BadArgValue" in str(refused[0])
        assert value.items is retained
        with pytest.raises(EngineError, match="BadArgValue"):
            ClassRefinedContainer([3])
        plan = declaration(ClassRefinedContainer)
        alternatives = plan.field_types(plan.field("items").annotation)
        assert alternatives and all(atom.head == S.Annotated for atom in alternatives)
        assert all(atom.args[-1] == S.MinLen(2) for atom in alternatives)
        replacement = (4, 5, 6)
        value.items = replacement
        assert value.items is replacement


@pytest.mark.parametrize("base", [object, Space])
@pytest.mark.parametrize("kind", [list, tuple, dict, set])
def test_length_refinements_follow_each_retained_container(base, kind):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClassSizedContainer(base):
            items: Annotated[kind, at.MinLen(2), at.MaxLen(3)]

        def supplied(size):
            return kind({index: index for index in range(size)})

        retained = supplied(2)
        value = ClassSizedContainer(retained)
        assert value.items is retained
        for size in (1, 4):
            with pytest.raises(EngineError, match="BadArgValue"):
                value.items = supplied(size)
            assert value.items is retained
        replacement = supplied(3)
        value.items = replacement
        assert value.items is replacement
