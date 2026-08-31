"""Purpose: keep pruned evaluation and non-reduction as different observable outcomes.
Guarantees:
  - eager eval returns no atoms for Empty and the written atom for
    NotReducible, while eval_status names both paths, including after a
    bound substitution [tested:
    test_eager_eval_keeps_empty_and_not_reducible_distinct; commit=4a5325f86c83a301673099e0f6281cae0ec6595c]
  - reducible() asks the head question without evaluating and agrees with
    eval_status on every outcome [tested:
    test_reducible_asks_the_question_without_running_the_term; commit=4a5325f86c83a301673099e0f6281cae0ec6595c]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

from metta import S


def test_eager_eval_keeps_empty_and_not_reducible_distinct(metta):
    """Two ways of answering nothing, and neither is a failure.

    `(empty)` PRUNES: the branch is gone and there is no answer. An
    unreduced term is its own ANSWER, which is not a lesser outcome but the
    language's ordinary one -- `!(hello world)` answers `(hello world)`, and
    that is the whole of hello world here. eval_status names which happened,
    as data, for a caller who wants to decide about it; there is no scope
    that turns the second into an error, because it is not one.
    """
    m = metta._new_space()
    unreduced = S.UnknownHead(1)

    assert m.eval(S.empty()) == []
    assert m.eval(unreduced) == [unreduced]
    assert m.eval_status(S.empty()) == [("empty", None)]
    assert m.eval_status(unreduced) == [("not-reducible", unreduced)]

    # A bound substitution lands BEFORE the reducibility question, so the
    # status names the substituted term rather than the written one.
    with m.bind({"placeholder": 7}):
        assert m.eval_status(S.UnknownHead(S.placeholder)) == [
            ("not-reducible", S.UnknownHead(7))
        ]
        assert m.eval(S.UnknownHead(S.placeholder)) == [S.UnknownHead(7)]


def test_reducible_asks_the_question_without_running_the_term(metta):
    """The developer-side check, which is why no scope needs to raise.

    A term nothing applies to is its own answer, so deciding what to do
    about one belongs to the caller. reducible() is that decision's input:
    the same head test eval_status uses, asked on its own, without running
    the term to find out. The Node seat has had m.reducible() since it
    existed and this seat had only eval_status [measured 2026-08-31].
    """
    m = metta._new_space()
    m.run("(= (twice $x) (* $x 2))")

    assert m.reducible(S.twice(4)) is True
    assert m.reducible(S.NoSuchHead(1, 2)) is False
    # It agrees with the status door, which is the same question answered
    # the long way round.
    for term in (S.twice(4), S.NoSuchHead(1, 2)):
        reduced = m.eval_status(term)[0][0] == "value"
        assert m.reducible(term) is reduced
