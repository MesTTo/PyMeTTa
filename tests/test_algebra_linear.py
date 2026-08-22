"""Purpose: black-box acceptance for the P4.30 linear algebra rung.

Guarantees:
  - the same stored evidence occurrence cannot satisfy two premises when its
    algebra deliberately omits contraction [tested:
    test_a_linear_algebra_refuses_the_second_spend_of_one_premise;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S
from petta.algebra import LinearEvidenceError


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
    with metta._new_space() as program:
        program.declare_annotations(
            program.name, "p4-linear", capabilities=("linear",)
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
    with metta._new_space() as reusable:
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
