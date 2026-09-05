"""Purpose: preserve lazy case selection for every Error expression arity."""

import pytest

from metta import S, V, fn


@pytest.mark.parametrize(
    "error",
    (S.Error(), S.Error(S.source), S.Error(S.source, S.reason),
     S.Error(S.source, S.reason, S.extra)),
)
def test_error_case_matches_every_error_head_without_running_the_other_arm(
    scratch_space, error
):
    """An anonymous segment recognizes the head without assuming payload width."""
    term = fn.case(error, ((S.Error(...), S.picked), (V._, fn.empty())))
    assert scratch_space.eval(term) == [S.picked]


def test_error_case_runs_only_the_selected_ordinary_arm(scratch_space):
    """The ordinary branch evaluates while its empty error arm stays unused."""
    term = fn.case(S.ordinary, ((S.Error(...), fn.empty()), (V._, V.x + 1)))
    assert scratch_space.eval(fn.let(V.x, 2, term)) == [3]
