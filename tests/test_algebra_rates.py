"""Purpose: black-box acceptance for the P4.29 declared-rate consumer.

Guarantees:
  - a seeded two-branch histogram matches its declared ratio while ordinary
    queries stay unchanged [tested:
    test_declared_rates_make_seeded_selection_match_their_distribution;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S, V, parse
from petta.algebra import RateDeclarationError


def test_declared_rates_make_seeded_selection_match_their_distribution(metta):
    """Match a declared 1:3 ratio reproducibly over one thousand draws."""
    metta.declare_algebra(
        "p4-rates",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    with metta._new_space() as program:
        program.add(S.ordinary(S.stays))
        unchanged = program.query(S.ordinary(V.value))
        program.add_tagged_fact(parse("(rate 1)"), S.branch(S.slow))
        program.add_tagged_fact(parse("(rate 3)"), S.branch(S.fast))
        first = program.sample_rates(
            S.branch(V.which), algebra="p4-rates", draws=1_000, seed=20260821
        )
        second = program.sample_rates(
            S.branch(V.which), algebra="p4-rates", draws=1_000, seed=20260821
        )
        assert first == second
        slow = sum(answer == S.branch(S.slow) for answer in first)
        fast = sum(answer == S.branch(S.fast) for answer in first)
        assert slow + fast == 1_000
        assert abs(slow / 1_000 - 0.25) <= 0.05
        assert abs(fast / 1_000 - 0.75) <= 0.05
        assert program.query(S.ordinary(V.value)) == unchanged


def test_invalid_rates_are_refused_before_the_tagged_fact_lands(metta):
    """Reject negative and nonnumeric rate tags at the public storage door."""
    with metta._new_space() as program:
        with pytest.raises(RateDeclarationError, match="negative_or_nonfinite_rate"):
            program.add_tagged_fact(parse("(rate -1)"), S.branch(S.invalid))
        with pytest.raises(RateDeclarationError, match="rate_not_numeric"):
            program.add_tagged_fact(parse("(rate nope)"), S.branch(S.invalid))
        assert len(program) == 0
