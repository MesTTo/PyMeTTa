"""Purpose: pin exhaustive finite tensor carriers to shape and value equality.

Guarantees:
  - both declaration doors certify the complete two-coordinate Boolean
    max-product semiring [tested: test_finite_tensor_semiring_checks_every_law;
    commit=074dc0a88b1605c54824de677d586b6f60998bcf].
"""

from itertools import product

import numpy as np
import pytest

from metta import S
from metta import algebra as algebra_module
from metta.algebra import AlgebraDeclarationError, AlgebraLawError


@pytest.mark.parametrize("door", ["space", "module"])
def test_finite_tensor_semiring_checks_every_law(metta, door):
    """Fresh operation results belong by value to the four-element carrier."""
    carrier = tuple(np.array(pair) for pair in product((0, 1), repeat=2))
    laws = (
        "combine-associative", "combine-commutative", "combine-idempotent",
        "extend-associative", "extend-commutative", "left-distributive",
        "right-distributive", "combine-zero-identity", "extend-one-identity",
        "extend-zero-annihilates",
    )
    with metta._new_space() as program:
        name = f"finite-tensor-{door}"
        if door == "space":
            program.op(lambda a, b: np.maximum(a, b), name=f"{name}-plus", effect="pureStructural")
            program.op(lambda a, b: np.multiply(a, b), name=f"{name}-times", effect="pureStructural")
            program.algebra(
                name, combine=f"{name}-plus", extend=f"{name}-times",
                zero=carrier[0], one=carrier[-1], carrier=carrier, laws=laws,
            )
            declared = algebra_module.require(program, name)
        else:
            with program:
                declared = algebra_module(
                    name, plus=np.maximum, times=np.multiply,
                    zero=carrier[0], one=carrier[-1], carrier=carrier, laws=laws,
                )
        assert declared.laws == frozenset(laws)
        program.add_tagged_fact(np.array([1, 0]), S.tensor_fact(S.left))
        program.add_tagged_fact(np.array([1, 1]), S.tensor_fact(S.right))
        program.add_tagged_rule(
            np.array([1, 1]), S.tensor_join(),
            S.tensor_fact(S.left), S.tensor_fact(S.right),
        )
        result = program.match(S.tensor_join(), under=declared).one()
        np.testing.assert_array_equal(result.annotation, [1, 0])


def test_finite_tensor_carrier_rejects_broadcast_equal_shapes(metta):
    """Broadcast-compatible values with different shapes are distinct."""
    with metta._new_space() as program:
        with program, pytest.raises(AlgebraLawError, match="algebra_carrier_not_closed"):
            algebra_module(
                "tensor-shape-refusal", plus=lambda a, b: (a + b).reshape(1, 2),
                times=np.multiply, zero=np.array([0, 0]), one=np.array([1, 1]),
                carrier=(np.array([0, 0]), np.array([1, 1])),
                laws=("combine-associative",),
            )


def test_finite_tensor_law_refusal_names_the_equation(metta):
    """Closed tensor subtraction modulo three fails associativity by value."""
    with metta._new_space() as program:
        with program, pytest.raises(AlgebraLawError, match=r"algebra_law_violation.*combine-associative"):
            algebra_module(
                "tensor-false-law", plus=lambda a, b: (a - b) % 3,
                times=lambda a, b: (a * b) % 3, zero=np.array([0]), one=np.array([1]),
                carrier=tuple(np.array([n]) for n in range(3)),
                laws=("combine-associative",),
            )


def test_finite_tensor_nan_does_not_become_equal_by_identity(metta):
    """The very same NaN-bearing tensor still fails exact value membership."""
    value = np.array([np.nan])
    with metta._new_space() as program:
        with program, pytest.raises(AlgebraDeclarationError, match="algebra_value_outside_carrier"):
            algebra_module(
                "tensor-nan-refusal", plus=lambda a, _b: a, times=lambda a, _b: a,
                zero=value, one=value, carrier=(value,),
                laws=("combine-associative",),
            )
