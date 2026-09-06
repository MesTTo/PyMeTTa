"""Purpose: pin one refusal for a grounded value with several type witnesses.

Guarantees:
  - scalar multiplication reports the concrete array class once, and bag
    evaluation reports its type failure rather than a cardinality failure
    [tested: this module; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
Owns resources: the protocol fixture removes its two registrations on every exit.
"""

import pytest

from metta import S, arrays, ground, integrate
from metta.algebra import AlgebraOperationError

numpy = pytest.importorskip("numpy")


@pytest.fixture()
def tensor_type():
    """Register named and shaped witnesses independently of operation setup."""
    integrate.register_object_type(arrays.is_array, "DLTensor")
    integrate.register_object_type(arrays.is_array, arrays._array_type)
    try:
        yield
    finally:
        integrate.unregister_object_type(arrays.is_array, arrays._array_type)
        integrate.unregister_object_type(arrays.is_array, "DLTensor")


def test_an_array_product_reports_one_concrete_type_refusal(scratch_space, tensor_type):
    """The concrete class and DLTensor protocol describe the same operand."""
    del tensor_type
    left = ground(numpy.array([2.0, 3.0]))
    right = ground(numpy.array([4.0, 5.0]))
    assert list(scratch_space.eval(S.get_type(left))) == [
        S.Annotated(S.DLTensor, arrays.Shape(2)), S.ndarray, S.DLTensor,
    ]
    call = S["*"](left, right)
    expected = S.Error(call, S.BadArgType(1, S.Number, S.ndarray))
    assert scratch_space.eval(call) == [expected]
    assert scratch_space.eval(S["+"](1, call)) == [expected]


def test_an_accepted_protocol_leaves_only_the_later_wrong_argument(scratch_space, tensor_type):
    """A class mismatch cannot blame a parameter its protocol accepts."""
    del tensor_type
    value = ground(numpy.array([2.0, 3.0]))
    scratch_space.run("(: tensor-and-number (-> DLTensor Number Number))")
    call = S.tensor_and_number(value, "bad")
    assert scratch_space.eval(call) == [
        S.Error(call, S.BadArgType(2, S.Number, S.String)),
    ]


def test_bag_over_tensor_tags_reports_the_type_failure(scratch_space, tensor_type):
    """One failed scalar operation remains a named refusal in the algebra."""
    del tensor_type
    left = ground(numpy.array([2.0, 3.0]))
    right = ground(numpy.array([4.0, 5.0]))
    scratch_space.add_tagged_fact(left, S.left(S.a))
    scratch_space.add_tagged_fact(right, S.right(S.b))
    scratch_space.add_tagged_rule(1, S.joined(S.a), S.left(S.a), S.right(S.b))
    with pytest.raises(AlgebraOperationError, match="BadArgType") as refusal:
        list(scratch_space.match(S.joined(S.a), under="bag"))
    assert "BadArgType 2 Number ndarray" in str(refusal.value)
    assert "algebra_operation_not_single" not in str(refusal.value)
    assert "ErrorType" not in str(refusal.value)
    assert refusal.value.atom == S.Error(
        S["*"](1, left), S.BadArgType(2, S.Number, S.ndarray),
    )


def test_an_error_tag_preserves_its_original_refusal(scratch_space):
    """An existing refusal must not become a fresh ErrorType mismatch."""
    error = S.Error(S["*"]("bad", 2), S.BadArgType(1, S.Number, S.String))
    scratch_space.add_tagged_fact(error, S.source(S.a))
    scratch_space.add_tagged_rule(1, S.target(S.a), S.source(S.a))
    with pytest.raises(AlgebraOperationError, match="BadArgType") as refusal:
        list(scratch_space.match(S.target(S.a), under="bag"))
    assert refusal.value.atom == error
    assert "ErrorType" not in str(refusal.value)
