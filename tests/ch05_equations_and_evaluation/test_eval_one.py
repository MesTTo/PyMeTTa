"""Purpose: preserve the native one-answer contract at the Python boundary.

Successful false, empty and Error values remain data; zero and multiple
answers raise the native cardinality error [tested:
sh extensions/python/test.sh tests/ch05_equations_and_evaluation/test_eval_one.py -n 0,
eight cases; commit=WORKTREE].
"""

import pytest

from metta import Expression, S
from metta._errors.errors import EngineError


@pytest.mark.parametrize("value", [None, False, Expression(), S.Error(S.held, S.data), S["+"](2, 3)])
def test_one_answer_returns_its_completed_value(metta, value):
    """Value shape cannot turn unique success into failure or another call."""
    assert metta.eval(S.eval_one(S.noeval(value))) == [value]


@pytest.mark.parametrize("answers", [(), (1, 2), (1, 1)])
def test_non_unique_answers_raise_the_native_cardinality_error(metta, answers):
    """Zero, different and duplicate answers keep the same native refusal."""
    with pytest.raises(EngineError, match=r"declares one cardinality.*evaluation must produce exactly one answer"):
        metta.eval(S.eval_one(S.superpose(answers)))
