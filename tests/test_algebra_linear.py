"""Purpose: black-box acceptance for the P4.30 linear algebra rung.

Guarantees:
  - the same stored evidence occurrence cannot satisfy two premises when its
    algebra deliberately omits contraction [tested:
    test_a_linear_algebra_refuses_the_second_spend_of_one_premise;
    commit=1822ca53390b180e622f262b766f224ae7a9278f]
"""

import pytest

from petta import LinearEvidenceError, S


def test_a_linear_algebra_refuses_the_second_spend_of_one_premise(metta):
    """Refuse one meeting token serving two premises in one derivation."""
    metta.declare_algebra(
        "p4-linear",
        combine="max",
        extend="+",
        zero=0,
        one=0,
        requires=("linear",),
    )
    with metta.new_space() as program:
        program.declare_annotations(
            program.space_name, "p4-linear", capabilities=("linear",)
        )
        program.add_tagged_fact(1, S.meeting_token(S.alice, S.room7))
        program.add_tagged_rule(
            0,
            S.double_booked(S.alice),
            S.meeting_token(S.alice, S.room7),
            S.meeting_token(S.alice, S.room7),
        )
        with pytest.raises(
            LinearEvidenceError,
            match=r"linear_evidence_already_spent\(p4-linear, token=\d+\)",
        ):
            program.evaluate_algebra(
                S.double_booked(S.alice), algebra="p4-linear"
            )

    metta.declare_algebra(
        "p4-reusable-evidence",
        combine="max",
        extend="+",
        zero=0,
        one=0,
    )
    with metta.new_space() as reusable:
        reusable.add_tagged_fact(1, S.meeting_token(S.alice, S.room7))
        reusable.add_tagged_rule(
            0,
            S.double_booked(S.alice),
            S.meeting_token(S.alice, S.room7),
            S.meeting_token(S.alice, S.room7),
        )
        answers = reusable.evaluate_algebra(
            S.double_booked(S.alice), algebra="p4-reusable-evidence"
        ).answers
        assert [(str(answer.value), str(answer.tag)) for answer in answers] == [
            ("(double_booked alice)", "2")
        ]
