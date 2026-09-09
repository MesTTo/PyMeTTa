"""Purpose: a failing comparison over answers hands its two bag differences over as data.

A harness reports what was missing and what was in excess without parsing the
engine's sentence. The differences are not new work: assertEqualToResult has
always computed both to decide its verdict and kept only their emptiness, and
assertEqual's two collapsed tuples are the same two bags. What changed is that
they now reach the failure instead of being discarded with the comparison.

Guarantees:
  - a two-sided difference arrives as .missing and .excess, tuples of decoded
    atoms, and the same two lines are in the message
    [tested: test_a_two_sided_difference_arrives_as_two_bags]
  - each one-sided difference reports the empty tuple on its other side, which
    is a different answer from absence
    [tested: test_an_answer_only_missing_reports_an_empty_excess,
    test_an_answer_only_in_excess_reports_an_empty_missing]
  - two empty bags say the answers agree and differ only in order, which is
    the one thing assertEqual's order-sensitive verdict can fail on while the
    bags agree [tested: test_two_empty_bags_mean_the_answers_differ_in_order]
  - a failing form that computed no bag difference reports None for both, so
    absence and emptiness stay tellable apart
    [tested: test_a_form_with_no_bag_comparison_reports_neither_bag]
  - a one-sided comparison reports the one bag its verdict depended on and
    None for the other, so an answer the relation ALLOWS is never named as a
    reason for the failure
    [tested: test_a_containment_reports_the_missing_bag_alone]
  - multiplicity survives the crossing: one occurrence on one side consumes
    exactly one on the other
    [tested: test_the_bags_keep_their_multiplicity]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from metta import MeTTa, S
from metta._errors.errors import AssertionFailure


@pytest.fixture(name="space")
def _space():
    return MeTTa().self


def failure(space, source: str) -> AssertionFailure:
    """The AssertionFailure one false claim raises."""
    with pytest.raises(AssertionFailure) as caught:
        space.run(source)
    return caught.value


def test_a_two_sided_difference_arrives_as_two_bags(space):
    """Both directions of a difference at once.

    3 was wanted and never produced, 2 was produced and never wanted. The
    message carries the same two lines, because the engine's own sentence
    does, so nothing here is a second spelling of the diagnosis.
    """
    caught = failure(space, "!(assertEqual (+ 1 1) 3)")

    assert caught.missing == (3,)
    assert caught.excess == (2,)
    assert "missing: (3)" in str(caught)
    assert "excess: (2)" in str(caught)
    # The form is the call as the program wrote it, not the False it reduced
    # to, so the report names something a reader can find in the source.
    assert "(assertEqual (+ 1 1) 3)" in str(caught)


def test_an_answer_only_missing_reports_an_empty_excess(space):
    """An expectation nothing produced.

    The other side is EMPTY rather than absent: the comparison ran and found
    nothing in excess.
    """
    caught = failure(space, "!(assertEqualToResult (superpose (1 2)) (1 2 3))")

    assert caught.missing == (3,)
    assert caught.excess == ()


def test_an_answer_only_in_excess_reports_an_empty_missing(space):
    """The mirror: everything expected was produced, and one answer more."""
    caught = failure(space, "!(assertEqualToResult (superpose (1 2 3)) (1 2))")

    assert caught.missing == ()
    assert caught.excess == (3,)


def test_two_empty_bags_mean_the_answers_differ_in_order(space):
    """Two empty bags beside a failure are the diagnosis, not a puzzle.

    The verdict is term equality over the collapsed tuples, so a permutation
    fails while the two bags agree, and the message says which one it is.
    """
    caught = failure(space, "!(assertEqual (superpose (1 2)) (superpose (2 1)))")

    assert caught.missing == ()
    assert caught.excess == ()
    assert "differ only in order" in str(caught)


def test_the_bags_keep_their_multiplicity(space):
    """A bag difference, not a set difference.

    (a a b) against (a b b) leaves one b wanted and one a produced, and the
    counts are what say so.
    """
    caught = failure(space, "!(assertEqual (superpose (a a b)) (superpose (a b b)))")

    assert caught.missing == (S.b,)
    assert caught.excess == (S.a,)


def test_a_containment_reports_the_missing_bag_alone(space):
    """A containment asks a one-sided question and gets a one-sided answer.

    7 was expected and never produced, which is the whole reason the claim
    failed. 1 and 2 were produced and never expected, and this relation ALLOWS
    that, so naming them would point the reader at something that is not
    broken: the excess side is absent rather than empty, and absence is what
    None says.
    """
    caught = failure(space, "!(assertIncludes (superpose (1 2)) (7))")

    assert caught.missing == (7,)
    assert caught.excess is None
    assert "missing: (7)" in str(caught)
    assert "excess" not in str(caught)
    assert "(assertIncludes (superpose (1 2)) (7))" in str(caught)


def test_a_form_with_no_bag_comparison_reports_neither_bag(space):
    """A verdict is not two answer bags, so there is no difference to report.

    None and () are different answers, and a harness that treated them alike
    would report "nothing missing" for a form that never compared anything.
    """
    caught = failure(space, "!(assert (== 1 2))")

    assert caught.missing is None
    assert caught.excess is None
    assert "missing:" not in str(caught)

    # A failing (test ...) is the other formal with no bag comparison, and it
    # keeps carrying its own pair instead.
    from_test = failure(space, "!(test (+ 1 1) 3)")
    assert from_test.missing is None
    assert from_test.excess is None
    assert from_test.actual == 2


def test_the_message_a_msg_variant_carries_names_its_own_call(space):
    """The Msg forms accept a message the engine used to drop on the floor.

    Reporting the call as written carries it, so the author's sentence is in
    the failure with no separate channel for it.
    """
    caught = failure(space, '!(assertEqualMsg (+ 1 2) 4 "sums differ")')

    assert "sums differ" in str(caught)
    assert caught.missing == (4,)
    assert caught.excess == (3,)
