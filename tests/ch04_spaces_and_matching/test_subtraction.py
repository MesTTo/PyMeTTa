"""Purpose: verify single-occurrence subtraction inside native transactions.

Guarantees: a missing occurrence returns False, each successful call consumes
one copy, and rollback restores every consumed copy [tested:
test_subtraction_in_a_transaction_preserves_multiplicity; commit=8806bbf1f5fb8ff233e2ed4868190757d4fb7041].
Owns resources: each generated case creates and drops its own space.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import metta as metta_package
from metta import FALSE, TRUE, S, V


@pytest.mark.parametrize("atom", [S.subtraction_item(1), S.subtraction_item])
@pytest.mark.parametrize("language", [False, True], ids=["python", "metta"])
@given(
    copies=st.integers(min_value=0, max_value=12),
    attempts=st.integers(min_value=1, max_value=16),
    rollback=st.booleans(),
)
def test_subtraction_in_a_transaction_preserves_multiplicity(
    atom, language, copies, attempts, rollback,
):
    """Neither native door waits for an absent atom or consumes a second copy."""
    with metta_package.space() as space:
        if copies:
            space.add(*([atom] * copies))

        def work():
            for attempt in range(attempts):
                present = attempt < copies
                if language:
                    assert space.eval(S["subtract-atom"](space, atom)) == [
                        TRUE if present else FALSE,
                    ]
                else:
                    assert space.remove(atom) is present
                assert list(space.atoms()) == [atom] * max(0, copies - attempt - 1)
            if rollback:
                message = "restore the consumed occurrences"
                raise RuntimeError(message)

        if rollback:
            with pytest.raises(RuntimeError, match="restore the consumed occurrences"):
                space.transaction(work)
            remaining = copies
        else:
            space.transaction(work)
            remaining = max(0, copies - attempts)
        assert list(space.atoms()) == [atom] * remaining


def test_subtraction_accepts_a_structured_pattern_and_keeps_its_variables_free():
    """A repeated pattern selects one occurrence anew on each call."""
    with metta_package.space() as space:
        space.add(S.subtraction_pair(1), S.subtraction_pair(2))
        assert space.run(
            "!(transaction (progn "
            "(subtract-atom &self (subtraction-pair $x)) "
            "(subtract-atom &self (subtraction-pair $x)) $x))"
        ) == [[V.x]]
        assert list(space.atoms()) == []
