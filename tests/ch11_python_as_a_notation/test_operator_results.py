"""Purpose: preserve Python operator result values across native application.

Guarantees: a successful None is one answer; container and Atom results retain
their identity when returned and when another callable consumes them
[tested: test_compiled_operator_results_retain_identity_and_later_use;
commit=fb170a48db042c9a002e06f6cb47389af7fd66fc].
Guarantees: declared instance and class results retain their native images
[tested: test_compiled_operator_results_keep_declared_images; commit=fb170a48db042c9a002e06f6cb47389af7fd66fc].
Owns resources: isolated fixture spaces retire plain functions; MeTTa contexts
retire class programs, instances and their grounded values.
"""

import operator
from dataclasses import dataclass

import pytest

from metta import Expression, MeTTa, S, Space, V, convert, testing
from metta._declare.classes import declaration


class _ResultOperand:
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return self.value


def test_compiled_operator_results_retain_identity_and_later_use(scratch_space):
    """The actual addition protocol returns data through the shared service."""

    @scratch_space.define
    def result(operand):
        return operator.add(operand, 0)

    @scratch_space.define
    def consume(operand, observer):
        value = operator.add(operand, 0)
        return observer(value)

    held = S.OperatorResult(S.payload)
    scratch_space.add(S["="](held, S.UnwantedReduction))
    assert scratch_space.eval(held) == [S.UnwantedReduction]
    for value in (None, False, 0, "", [], (1, 2), {}, set(), object(), held):
        seen = []

        def observe(item, *, expected=value, seen=seen):
            seen.append(item)
            return item is expected

        operand = _ResultOperand(value)
        assert result(operand).one() is value, type(value)
        assert consume(operand, observe).one() is True, (type(value), value, seen)
        assert len(seen) == 1 and seen[0] is value

    values = []

    def append(items):
        items.append(7)
        return items is values

    assert consume(_ResultOperand(values), append).one() is True
    assert values == [7]


def test_operator_result_twins_compare_nested_value_projections(scratch_space):
    """A borrowed result and its Python twin share the public structural image."""

    @scratch_space.define
    def nested(operand):
        return ("result", operator.add(operand, 0))

    for value in (None, [], [1, (2, 3)], (1, [2, 3])):
        assert testing.check_twin(nested, [(_ResultOperand(value),)])


def test_native_sequence_operator_results_retain_images(scratch_space):
    """Proved sequence results feed subsequent native bindings and operations."""
    @scratch_space.define
    def combine():
        values = [1, 2] + [3]  # noqa: RUF005 -- exercise operator lowering
        values += [4]
        return values + [5], (1, 2) * 2, 2 * (3, 4)  # noqa: RUF005

    assert list(combine()) == [Expression([
        Expression([1, 2, 3, 4, 5]), Expression([1, 2, 1, 2]),
        Expression([3, 4, 3, 4]),
    ])]


def test_unknown_reflected_sequence_result_remains_borrowed(scratch_space):
    """A native left operand does not prove an arbitrary reflected result type."""
    values = []

    class Reflected:
        def __radd__(self, other):
            return values

    @scratch_space.define
    def apply(operand):
        return [1] + operand  # noqa: RUF005 -- exercise reflected addition

    assert apply(Reflected()).one() is values


@pytest.mark.parametrize("grain", ("value", "entity", "prototype"))
def test_compiled_operator_results_keep_declared_images(grain):
    """Returned declarations still feed rewritten native methods and constructors."""
    with MeTTa() as context:
        metta = context.self
        base = Space if grain == "prototype" else object

        @metta.define
        @dataclass(frozen=grain == "value")
        class OperatorProduct(base):
            value: int

            def doubled(self) -> int:
                return self.value * 2

        @metta.define
        def inspect_instance(value: OperatorProduct) -> int:
            return value.value + value.doubled()

        @metta.define
        def consume_instance(operand):
            return inspect_instance(operator.add(operand, 0))

        @metta.define
        def consume_class(operand):
            return inspect_instance(operator.add(operand, 0)(9))

        @metta.define
        def return_class(operand):
            return operator.add(operand, 0)

        instance = _ResultOperand(OperatorProduct(4))
        assert consume_instance(instance).one() == 12
        owner = declaration(OperatorProduct)
        method = owner.methods["doubled"]
        assert method.compiled is not None
        owner.space.remove(S["="](S[method.name](V.self), V.body))
        owner.space.add(S["="](S[method.name](V.self), 30))
        assert consume_instance(instance).one() == 34
        returned = _ResultOperand(OperatorProduct)
        assert consume_class(returned).one() == 39
        assert convert.build(return_class(returned).one(), type) is OperatorProduct
