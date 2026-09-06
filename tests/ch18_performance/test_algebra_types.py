"""Purpose: check algebra carrier types independently of finite law certificates.

Guarantees:
  - tensor operations check input and output membership through both constructors
    [tested: test_tensor_type_carrier_runs_max_product_and_reinterprets_provenance; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - a type cannot confer a law certificate and every refusal names its remedy
    [tested: test_type_carrier_cannot_certify_laws; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
"""
import importlib

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import S, V, ground
from metta.algebra import AlgebraDeclarationError, AlgebraLawError, AlgebraOperationError


@pytest.mark.parametrize("door", ["space", "module"])
@pytest.mark.parametrize("kind", ["python", "metta", "predicate"])
def test_tensor_type_carrier_runs_max_product_and_reinterprets_provenance(metta, door, kind):
    """Both constructors admit tensors and retain uncertified alternatives."""
    algebra = importlib.import_module("metta.algebra")
    specification = {
        "python": np.ndarray,
        "metta": S.ndarray,
        "predicate": lambda value: isinstance(value, np.ndarray) and value.shape == (2,),
    }[kind]
    with metta._new_space() as space:
        name = f"typed-max-product-{door}-{kind}"
        plus, times = f"{name}-plus", f"{name}-times"
        try:
            if door == "module":
                with space:
                    declared = algebra(name, plus=np.maximum, times=np.multiply,
                                       zero=np.zeros(2), one=np.ones(2), type=specification)
            else:
                space.op(lambda a, b: np.maximum(a, b), name=plus, effect="pureStructural")
                space.op(lambda a, b: np.multiply(a, b), name=times, effect="pureStructural")
                row = space.algebra(name, combine=plus, extend=times,
                                    zero=np.zeros(2), one=np.ones(2), type=specification)
                assert row[7].head == S.type
                declared = algebra.require(space, name)
            space.add_tagged_fact(ground(np.array([0.2, 0.7])), S.edge(S.a))
            space.add_tagged_fact(ground(np.array([0.8, 0.3])), S.edge(S.a))
            space.add_tagged_rule(ground(np.array([0.5, 0.5])), S.result(V.x), S.edge(V.x))
            answers = list(space.match(S.result(S.a), under=declared))
            assert len(answers) == 2
            assert not answers[0].plan[0].applied
            np.testing.assert_array_equal(answers[0].annotation, [0.1, 0.35])
            np.testing.assert_array_equal(answers[1].annotation, [0.4, 0.15])
            retained = space.match(S.result(S.a), under="prov").one()
            np.testing.assert_array_equal(retained.under(declared).annotation, [0.4, 0.35])
        finally:
            for operation in (plus, times):
                if operation in {str(row[1]) for row in metta._at("&metta").atoms() if getattr(row, "head", None) == S.op}:
                    space.unregister_op(operation)


@pytest.mark.parametrize("law", ["combine-associative", "contraction"])
def test_type_carrier_cannot_certify_laws(metta, law):
    """A type alone cannot grant any law capability."""
    with metta._new_space() as space:
        with pytest.raises(AlgebraLawError, match=r"finite carrier.*prov.*under"):
            space.algebra("uncertified-type", combine="max", extend="*", zero=0, one=1,
                          type=int, laws=(law,))


@pytest.mark.parametrize("where", ["zero", "input", "result", "fact", "rule"])
def test_type_carrier_refuses_values_outside_its_type(metta, where):
    """Identities, operands, results and source annotations share membership."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        if where == "zero":
            with pytest.raises(AlgebraDeclarationError, match=r"algebra_value_outside_carrier.*type"):
                space.algebra("typed-refusal", combine="max", extend="*", zero="bad", one=1, type=int)
            return
        space.run('(= (typed-bad-result $a $b) "bad")')
        space.algebra("typed-refusal", combine="typed-bad-result", extend="*", zero=0, one=1, type=int)
        declared = algebra.require(space, "typed-refusal")
        with pytest.raises(AlgebraOperationError, match=r"algebra_value_outside_carrier.*type"):
            if where == "input":
                declared.extend_values(space, ground("bad"), ground(1))
            elif where == "result":
                declared.combine_values(space, ground(1), ground(2))
            else:
                space.add_tagged_fact("bad" if where == "fact" else 1, S.base(S.a))
                space.add_tagged_rule("bad" if where == "rule" else 1, S.result(S.a), S.base(S.a))
                list(space.match(S.result(S.a), under=declared))


def test_finite_carrier_rejects_runtime_values_outside_its_certificate(metta):
    """An exhausted domain constrains later runtime values too."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        space.algebra("finite-bits", combine="max", extend="*", zero=0, one=1,
                      carrier=(0, 1), laws=("combine-associative",))
        space.add_tagged_fact(2, S.base(S.a))
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            list(space.match(S.base(S.a), under=algebra.require(space, "finite-bits")))


def test_predicate_carrier_requires_one_boolean_answer(metta):
    """A truthy container is not a Boolean predicate answer."""
    with metta._new_space() as space:
        with pytest.raises(AlgebraDeclarationError, match=r"predicate.*bool"):
            space.algebra("predicate-not-bool", combine="max", extend="*", zero=0, one=1,
                          type=lambda _value: [True, False])


@given(left=st.integers(min_value=0, max_value=100), right=st.integers(min_value=0, max_value=100))
def test_predicate_carrier_checks_arbitrary_products(metta, left, right):
    """Nonnegative products satisfy the declared refinement predicate."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        space.algebra("nonnegative-product", combine="max", extend="*", zero=0, one=1,
                      type=lambda value: isinstance(value, int) and value >= 0)
        declared = algebra.require(space, "nonnegative-product")
        assert declared.extend_values(space, ground(left), ground(right)) == left * right


def test_refused_constructor_rolls_back_its_operations(metta):
    """A repaired declaration can reuse names from a refused constructor."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space, space:
        with pytest.raises(AlgebraDeclarationError, match="algebra_value_outside_carrier"):
            algebra("refused-constructor", plus=max, times=lambda a, b: a * b,
                    zero="bad", one=1, type=int)
        declared = algebra("refused-constructor", plus=max, times=lambda a, b: a * b,
                           zero=0, one=1, type=int)
        assert declared.extend_values(space, ground(2), ground(3)) == 6
        space.unregister_op("refused-constructor-plus")
        space.unregister_op("refused-constructor-times")
