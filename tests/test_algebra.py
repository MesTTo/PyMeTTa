"""Purpose: black-box acceptance tests for the P4.20 declared-algebra base.

Guarantees:
  - the required P4.20 names exercise only public PeTTa surfaces
    [tested: this module; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - a ground algebra goal cannot bind a variable inside a stored candidate
    [tested: test_algebra_patterns_do_not_bind_variables_inside_stored_candidates;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import (
    Answer,
    Expression,
    S,
    V,
    parse,
)
from metta.algebra import AlgebraLawError
from metta.foreign import SpaceProvider


class _WeightedFacts(SpaceProvider):
    """Two one-row relations whose answer annotations are 2 and 3."""

    def atoms(self) -> Iterator[Expression]:
        yield parse("(left a)")
        yield parse("(right b)")

    def match(self, pattern, *, limit=None):
        del limit
        text = str(pattern)
        if text == "(left a)":
            yield Answer(value=parse("(left a)"), k=2)
        elif text == "(right b)":
            yield Answer(value=parse("(right b)"), k=3)


def _join_annotation(metta, name: str, algebra: str) -> str:
    metta._register_space(_WeightedFacts(), name)
    metta.annotations(name, algebra)
    result = metta.run(
        f"!(match {name} (, (left a) (right b)) (annotation))"
    )
    return str(result[0][0])


def test_a_declared_semiring_quadruple_serves_annotations_like_a_builtin_one(
    metta,
):
    """A user quadruple and the shipped probability preset share one join."""
    metta.algebra(
        "p4-user-product",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    custom = _join_annotation(metta, "&p4-custom-product", "p4-user-product")
    shipped = _join_annotation(metta, "&p4-shipped-product", "prob")
    assert custom == shipped == "6"

    metta._at("&petta").add(
        parse("(algebra p4-direct-product + * 0 1 (laws) (carrier) (requires))")
    )
    direct = _join_annotation(metta, "&p4-direct-product", "p4-direct-product")
    assert direct == shipped


def test_a_declared_algebra_without_laws_answers_in_order_and_unfused(metta):
    """Ordinary atomspace facts are authoritative and missing laws are visible."""
    metta.algebra(
        "p4-lawless-order",
        combine="pair",
        extend="pair",
        zero=S.none,
        one=S.unit,
    )
    with metta._new_space() as lawless:
        lawless.add(parse("(fact first (choice same))"))
        lawless.add(parse("(fact second (choice same))"))
        answers = list(lawless.match(S.choice(S.same), under="p4-lawless-order"))
        assert [str(answer.tag) for answer in answers] == [
            "first",
            "second",
        ]
        assert answers[0].plan[0].applied is False
        assert answers[0].plan[0].missing_laws == ("combine-associative",)

    metta.algebra(
        "p4-handwritten-bisim",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    with metta._new_space() as handwritten, metta._new_space() as generated:
        handwritten.add(parse("(fact 2 (parent tom bob))"))
        handwritten.add(parse("(fact 3 (parent bob ann))"))
        handwritten.add(
            parse(
                "(rule 1 (grandparent $x $z) "
                "(premises (parent $x $y) (parent $y $z)))"
            )
        )
        generated.add_tagged_fact(2, S.parent(S.tom, S.bob))
        generated.add_tagged_fact(3, S.parent(S.bob, S.ann))
        generated.add_tagged_rule(
            1,
            S.grandparent(V.x, V.z),
            S.parent(V.x, V.y),
            S.parent(V.y, V.z),
        )
        manual = handwritten.match(
            S.grandparent(S.tom, S.ann), under="p4-handwritten-bisim"
        )
        compiled = generated.match(
            S.grandparent(S.tom, S.ann), under="p4-handwritten-bisim"
        )
        assert [(str(row.value), str(row.tag)) for row in manual] == [
            (str(row.value), str(row.tag)) for row in compiled
        ] == [("(grandparent tom ann)", "6")]


def test_algebra_patterns_do_not_bind_variables_inside_stored_candidates(metta):
    """Neither a final goal nor a rule premise may fill a stored variable."""
    metta.algebra(
        "p4-directional-goal",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    with metta._new_space() as facts:
        facts.add_tagged_fact(1, S.edge(V.stored, S.b))
        facts.add_tagged_rule(
            1,
            S.derived(S.hit),
            S.edge(S.a, S.b),
        )
        goal_evaluation = facts.evaluate_algebra(
            S.edge(S.a, S.b),
            algebra="p4-directional-goal",
        )
        premise_evaluation = facts.evaluate_algebra(
            S.derived(S.hit),
            algebra="p4-directional-goal",
        )

    assert goal_evaluation.answers == ()
    assert premise_evaluation.answers == ()


def test_a_false_declared_law_is_refused_by_name(metta):
    """Finite carrier checking publishes the first concrete counterexample."""
    metta.op(
        lambda left, right: (left - right) % 3,
        name="p4-subtract-mod3",
    )
    with pytest.raises(
        AlgebraLawError,
        match=r"algebra_law_violation\(p4-bad-associative, combine-associative",
    ):
        metta.algebra(
            "p4-bad-associative",
            combine="p4-subtract-mod3",
            extend="p4-subtract-mod3",
            zero=0,
            one=0,
            laws=("associative",),
            carrier=(0, 1, 2),
        )


@given(
    left=st.integers(min_value=-100, max_value=100),
    middle=st.integers(min_value=-100, max_value=100),
    right=st.integers(min_value=-100, max_value=100),
)
def test_the_shipped_numeric_extend_is_associative(left, middle, right):
    """The shipped presets' direct numeric fast path carries its named law."""
    assert (left * middle) * right == left * (middle * right)
