"""Purpose: preserve broad sequence equality without conflicting hash contracts."""

from collections.abc import Hashable

import pytest

from metta._spaces.results import Answers


@pytest.mark.parametrize("peer", ["ab", b"ab", range(2), (1, 2), [1, 2]])
def test_audit_a3_broad_sequence_equality_is_unhashable(peer):
    """Every admitted sequence peer remains equal without selecting its hash."""
    with Answers(peer) as answers:
        assert answers == peer
        assert peer == answers
        assert not isinstance(answers, Hashable)
        with pytest.raises(TypeError, match="unhashable"):
            hash(answers)


def test_refusing_answer_hashing_does_not_pull_the_source():
    """Hash refusal cannot run or drain an evaluation as a side effect."""
    pulled = []

    def source():
        pulled.append(True)
        yield 1

    with Answers(source()) as answers:
        with pytest.raises(TypeError, match="unhashable"):
            hash(answers)
        assert pulled == []
