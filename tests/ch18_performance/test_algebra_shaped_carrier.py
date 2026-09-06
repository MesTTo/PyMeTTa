"""Purpose: compose structural tensor type projection with algebra membership.

Guarantees:
  - fixed shape carriers check operands, results and finite certificate values
    [tested: test_shaped_carrier_accepts_products_and_refuses_other_shapes,
    test_shaped_finite_carrier_certifies_fresh_equal_arrays; commit=WORKTREE].
  - a refined operation failure remains one specific Error across algebra calls
    [tested: test_shaped_operation_refusal_is_one_algebra_error; commit=WORKTREE].
Owns resources: fixtures remove their protocol entries and operation registrations
  and drop every declaring space.
"""

from typing import Annotated

import numpy as np
import pytest

from metta import S, algebra, arrays, ground, integrate
from metta.algebra import AlgebraOperationError


@pytest.fixture
def shaped_array_protocol():
    """Use the live projector installed by arrays without changing global ops."""
    integrate.register_object_type(arrays.is_array, "DLTensor")
    integrate.register_object_type(arrays.is_array, arrays._array_type)
    try:
        yield
    finally:
        integrate.unregister_object_type(arrays.is_array, arrays._array_type)
        integrate.unregister_object_type(arrays.is_array, "DLTensor")


@pytest.mark.usefixtures("shaped_array_protocol")
@pytest.mark.parametrize("door", ["space", "module"])
def test_shaped_carrier_accepts_products_and_refuses_other_shapes(metta, door):
    """A native refined type constrains fresh array results at both public doors."""
    expected = S.Annotated(S.DLTensor, arrays.Shape(2, 3))
    with metta._new_space() as space, space:
        calls = []
        wrong_result = False
        name = f"fixed-shape-carrier-{door}"

        def times(left, right):
            calls.append((left.shape, right.shape))
            result = np.multiply(left, right)
            return result.reshape(3, 2) if wrong_result else result

        if door == "module":
            declared = algebra(name, plus=np.maximum, times=times,
                               zero=np.zeros((2, 3)), one=np.ones((2, 3)), type=expected)
        else:
            space.op(lambda a, b: np.maximum(a, b), name=f"{name}-plus", effect="pureStructural")
            space.op(times, name=f"{name}-times", effect="pureStructural")
            space.algebra(name, combine=f"{name}-plus", extend=f"{name}-times",
                          zero=np.zeros((2, 3)), one=np.ones((2, 3)), type=expected)
            declared = algebra.require(space, name)
        try:
            left, right = np.full((2, 3), 2), np.full((2, 3), 3)
            assert expected in space.eval(S.get_type(ground(left)))
            left_atom = ground(left)
            result = declared.extend_values(space, left_atom, ground(right))
            np.testing.assert_array_equal(arrays.data_of(result), np.full((2, 3), 6))
            assert not declared.laws
            space.add_tagged_fact(left, S.shaped_source)
            space.add_tagged_rule(right, S.shaped_result, S.shaped_source)
            answer = space.match(S.shaped_result, under=declared).one()
            np.testing.assert_array_equal(answer.annotation, np.full((2, 3), 6))
            assert not answer.plan[0].applied
            before = len(calls)
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                declared.extend_values(space, ground(left.reshape(3, 2)), ground(right))
            assert len(calls) == before
            # Reusing an admitted atom cannot preserve its obsolete shape.
            left.resize((3, 2), refcheck=False)
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                declared.extend_values(space, left_atom, ground(right))
            assert len(calls) == before
            left.resize((2, 3), refcheck=False)
            wrong_result = True
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                declared.extend_values(space, ground(left), ground(right))
            assert len(calls) == before + 1
        finally:
            space.unregister_op(f"{name}-times")
            space.unregister_op(f"{name}-plus")


@pytest.mark.usefixtures("shaped_array_protocol")
def test_shaped_finite_carrier_certifies_fresh_equal_arrays(metta):
    """Shape projection and exhaustive value equality constrain the same domain."""
    expected = S.Annotated(S.DLTensor, arrays.Shape(2, 3))
    with metta._new_space() as space, space:
        declared = algebra(
            "finite-shaped-carrier", plus=np.maximum, times=np.multiply,
            zero=np.zeros((2, 3)), one=np.ones((2, 3)), type=expected,
            carrier=(np.zeros((2, 3)), np.ones((2, 3))),
            laws=("combine-associative", "extend-associative", "left-distributive"),
        )
        try:
            result = declared.extend_values(space, ground(np.ones((2, 3))), ground(np.ones((2, 3))))
            np.testing.assert_array_equal(arrays.data_of(result), np.ones((2, 3)))
            assert len(declared.laws) == 3
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                declared.extend_values(space, ground(np.ones((1, 2, 3))), ground(np.ones((2, 3))))
        finally:
            space.unregister_op("finite-shaped-carrier-times")
            space.unregister_op("finite-shaped-carrier-plus")


@pytest.mark.usefixtures("shaped_array_protocol")
@pytest.mark.parametrize("door", ["host", "equation"])
def test_shaped_operation_refusal_is_one_algebra_error(metta, door):
    """Runtime shape evidence survives the ordinary and algebra refusal doors."""
    calls = []

    def product(
        left: Annotated[arrays.DLTensor, arrays.Shape(2, 3)],
        right: Annotated[arrays.DLTensor, arrays.Shape(2, 3)],
    ) -> arrays.DLTensor:
        calls.append((left, right))
        return np.multiply(left, right)

    with metta._new_space() as space:
        if door == "host":
            space.op(product, name="shape-constrained-product", effect="pureStructural", transport="raw")
        else:
            expected_type = S.Annotated(S.DLTensor, arrays.Shape(2, 3))
            space.run(
                f"(: shape-constrained-product (-> {expected_type} {expected_type} DLTensor)) "
                "(= (shape-constrained-product $left $right) $left)"
            )
        try:
            space.algebra("shape-operation-carrier", combine="shape-constrained-product",
                          extend="shape-constrained-product", zero=np.zeros((2, 3)),
                          one=np.ones((2, 3)), type=np.ndarray)
            declared = algebra.require(space, "shape-operation-carrier")
            bad, good = ground(np.ones((3, 2))), ground(np.ones((2, 3)))
            call = S.shape_constrained_product(bad, good)
            expected = S.Error(call, S.BadArgType(
                1, S.Annotated(S.DLTensor, arrays.Shape(2, 3)),
                S.Annotated(S.DLTensor, arrays.Shape(3, 2)),
            ))
            assert space.eval(call) == [expected]
            with pytest.raises(AlgebraOperationError, match="algebra_operation_error") as failure:
                declared.extend_values(space, bad, good)
            assert failure.value.atom == expected
            assert "algebra_operation_not_single" not in str(failure.value)
            assert calls == []
        finally:
            if door == "host":
                space.unregister_op("shape-constrained-product")
