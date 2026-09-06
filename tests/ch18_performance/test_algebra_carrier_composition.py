"""Purpose: check composition of algebra carrier types and finite certificates.

Guarantees:
  - native and Python types preserve text, symbols and declared type expressions
    [tested: test_carrier_preserves_text_and_symbol_types,
    test_native_type_expression_uses_declaring_space_witnesses; commit=074dc0a88b1605c54824de677d586b6f60998bcf].
  - a type and finite enumeration jointly constrain certified runtime values
    [tested: test_type_and_finite_carrier_check_both_constraints; commit=074dc0a88b1605c54824de677d586b6f60998bcf].
"""

import numpy as np
import pytest

from metta import Expression, S, Symbol, ground
from metta import algebra as algebra_module
from metta.algebra import AlgebraDeclarationError, AlgebraOperationError


@pytest.mark.parametrize("specification", [int, S.Number, lambda value: isinstance(value, int)])
def test_type_and_finite_carrier_check_both_constraints(metta, specification):
    """An int outside the complete finite domain cannot borrow its certificate."""
    with metta._new_space() as space:
        space.algebra(
            "typed-finite-bits", combine="max", extend="*", zero=0, one=1,
            type=specification, carrier=(0, 1), laws=("combine-associative",),
        )
        declared = algebra_module.require(space, "typed-finite-bits")
        assert declared.laws == frozenset(("combine-associative",))
        assert declared.extend_values(space, ground(1), ground(1)) == 1
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            declared.extend_values(space, ground(2), ground(1))
        space.add_tagged_fact(1, S.bits_fact())
        space.add_tagged_fact(1, S.bits_fact())
        answers = list(space.match(S.bits_fact(), under=declared))
        assert len(answers) == 1
        assert answers[0].annotation == 1
        assert answers[0].plan[0].applied


def test_finite_enumeration_must_satisfy_its_type(metta):
    """A finite member excluded by type cannot be certified or retained."""
    with metta._new_space() as space:
        with pytest.raises(AlgebraDeclarationError, match="algebra_value_outside_carrier"):
            space.algebra(
                "typed-invalid-member", combine="max", extend="*", zero=0, one=1,
                type=int, carrier=(0, 1, "bad"), laws=("combine-associative",),
            )
        assert algebra_module.get(space, "typed-invalid-member") is None


@pytest.mark.parametrize("specification,accepted,rejected", [
    (str, "word", S.word),
    (S.String, "word", S.word),
    (lambda value: isinstance(value, str), "word", S.word),
    (Symbol, S.word, "word"),
    (S.Symbol, S.word, "word"),
    (lambda value: isinstance(value, Symbol), S.word, "word"),
    (lambda value: isinstance(value, Expression), S.carrier_pair(1), "word"),
])
def test_carrier_preserves_text_and_symbol_types(metta, specification, accepted, rejected):
    """Text and symbols stay distinct even when their wire names agree."""
    with metta._new_space() as space:
        space.run("(= (carrier-first $left $right) $left)")
        space.algebra(
            "typed-text-symbol", combine="carrier-first", extend="carrier-first",
            zero=accepted, one=accepted, type=specification,
        )
        declared = algebra_module.require(space, "typed-text-symbol")
        atom = ground(accepted) if isinstance(accepted, str) else accepted
        assert declared.extend_values(space, atom, atom) == atom
        other = ground(rejected) if isinstance(rejected, str) else rejected
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            declared.extend_values(space, atom, other)


def test_class_decorator_reads_the_carrier_type_attribute(metta):
    """A decorated algebra's type attribute has the same membership contract."""
    with metta._new_space() as space, space:
        @algebra_module
        class TypedProduct:
            type = int
            zero = 0
            one = 1
            plus = staticmethod(max)

            @staticmethod
            def times(left, right):
                return left * right

        assert TypedProduct.type is int
        assert not TypedProduct.laws
        assert TypedProduct.extend_values(space, ground(2), ground(3)) == 6
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            TypedProduct.extend_values(space, ground(2), ground("3"))


def test_native_type_expression_uses_declaring_space_witnesses(metta):
    """A parametric type is checked through the same witnesses as get-type."""
    with metta._new_space() as space:
        space.run(
            "(: vector-zero (Vector Number)) "
            "(: vector-one (Vector Number)) "
            "(: vector-other (Vector String)) "
            "(= (carrier-first $left $right) $left)"
        )
        expected = S.Vector(S.Number)
        assert space.type(S.vector_zero) == expected
        space.algebra(
            "typed-vector", combine="carrier-first", extend="carrier-first",
            zero=S.vector_zero, one=S.vector_one, type=expected,
        )
        declared = algebra_module.require(space, "typed-vector")
        assert declared.extend_values(space, S.vector_zero, S.vector_one) == S.vector_zero
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            declared.extend_values(space, S.vector_zero, S.vector_other)


def test_typed_finite_certificate_rejects_equal_result_outside_type(metta):
    """Value equality cannot hide an operation result violating its type."""
    with metta._new_space() as space, space:
        with pytest.raises(AlgebraDeclarationError, match="algebra_value_outside_carrier"):
            algebra_module(
                "typed-finite-result", plus=lambda a, b: np.maximum(a, b).astype(np.int64),
                times=lambda a, b: a * b, zero=np.array([0], dtype=np.int16),
                one=np.array([1], dtype=np.int16),
                carrier=(np.array([0], dtype=np.int16), np.array([1], dtype=np.int16)),
                type=lambda value: isinstance(value, np.ndarray) and value.dtype == np.int16,
                laws=("combine-associative",),
            )
