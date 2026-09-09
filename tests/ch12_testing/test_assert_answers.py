"""Purpose: two answer bags compared in Python, and reported the way MeTTa reports them.

`assert_answers` and `assert_includes` are faces of the engine's own two
assertion doors rather than second implementations of them. That is what these
check: the same relation, the same two bag differences, the same sentence, so a
pytest failure and a MeTTa `assertEqualToResult` failure over the same bags are
read the same way by the same reader.

Guarantees:
  - order is not part of the comparison and multiplicity is
    [tested: test_a_permutation_passes, test_multiplicity_is_part_of_the_bag]
  - a false claim raises AssertionFailure carrying .missing and .excess, and
    the report under the first line is character-for-character the engine's own
    for the same two bags [tested: test_a_wrong_bag_names_what_is_missing_and_excess,
    test_the_report_is_the_engines_own_for_the_same_bags]
  - the containment face reports the missing bag ALONE, with excess absent
    rather than empty, because an answer in excess is legal under it
    [tested: test_a_containment_reports_the_missing_bag_alone]
  - a message rides in the reported call, the way the engine's Msg forms carry
    one [tested: test_a_message_rides_in_the_reported_call]
  - Rows, Answers and plain Python values are all answer bags
    [tested: test_a_query_answers_a_bag_three_ways]
  - one answer handed over as itself is refused with the sequence spelled out,
    a str included, which would otherwise compare character by character
    [tested: test_a_single_answer_is_refused_with_the_sequence_spelled_out]
  - the door starts the engine it needs, so an assertion can be the first line
    a test file runs [tested: test_the_first_line_of_a_test_file_can_be_an_assertion]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess
import sys

import pytest

from metta import Expression, S, V, testing
from metta._errors.errors import AssertionFailure


def failure(call) -> AssertionFailure:
    """The AssertionFailure one false claim raises."""
    with pytest.raises(AssertionFailure) as caught:
        call()
    return caught.value


def report(failure_: AssertionFailure) -> str:
    """The bag report, which is the part both faces share.

    The line above it names the call the program wrote, and those two calls are
    written in two languages, so it is the one line that differs by design.
    """
    return str(failure_).partition("\n")[2]


def test_a_permutation_passes():
    """Answer order within one query is unspecified, so it is not compared."""
    testing.assert_answers([1, 2, 3], [3, 1, 2])


def test_two_empty_bags_agree():
    """No answers on either side is the smallest agreement there is."""
    testing.assert_answers((), [])


def test_a_wrong_bag_names_what_is_missing_and_excess(scratch_space):
    """Both directions at once: 3 was wanted and never came, 2 came unwanted."""
    del scratch_space
    caught = failure(lambda: testing.assert_answers([1, 2], [1, 3]))

    assert caught.missing == (3,)
    assert caught.excess == (2,)
    assert "missing: (3)" in str(caught)
    assert "excess: (2)" in str(caught)
    # The reported call names the door that decided the verdict and shows the
    # two bags it decided over, so the failure is readable without the source.
    assert "(assert-answers (1 2) (1 3))" in str(caught)


def test_multiplicity_is_part_of_the_bag():
    """(a a b) is not (a b b), even though their ordinary sets agree."""
    caught = failure(lambda: testing.assert_answers([S.a, S.a, S.b], [S.a, S.b, S.b]))

    assert caught.missing == (S.b,)
    assert caught.excess == (S.a,)


def test_the_report_is_the_engines_own_for_the_same_bags(metta):
    """Drive both faces over the same two bags and compare the text.

    Everything below the first line is one renderer's output reached through
    one door, so this is what keeps the two faces from drifting: a Python-side
    difference would agree only until somebody changed one of them.
    """
    from_python = failure(lambda: testing.assert_answers([1, 2], [1, 2, 3]))
    from_metta = failure(
        lambda: metta.run("!(assertEqualToResult (superpose (1 2)) (1 2 3))")
    )

    assert report(from_python) == report(from_metta)
    assert report(from_python) == "  missing: (3)\n  excess: () (MeTTa assertion failed)"
    assert from_python.missing == from_metta.missing
    assert from_python.excess == from_metta.excess


def test_two_empty_bags_beside_a_failure_cannot_happen_here(metta):
    """The permutation note is the engine's, and this relation never reaches it.

    `assertEqual` compares the collapsed tuples with term equality, so it fails
    on a permutation while its two bags agree and the message says so. This
    face's verdict IS the bag difference, so agreeing bags are a pass and the
    note is unreachable through it -- which is worth pinning, because the note
    would be a contradiction here rather than a diagnosis.
    """
    testing.assert_answers([1, 2], [2, 1])
    assert "differ only in order" in str(
        failure(lambda: metta.run("!(assertEqual (superpose (1 2)) (superpose (2 1)))"))
    )


def test_a_containment_reports_the_missing_bag_alone():
    """A one-sided question gets a one-sided answer.

    1 and 2 were produced and never expected, and containment ALLOWS that, so
    naming them would point the reader at something that is not broken: the
    excess side is absent rather than empty, and absence is what None says.
    """
    testing.assert_includes([1, 2, 3], [1, 3])

    caught = failure(lambda: testing.assert_includes([1, 2], [7]))
    assert caught.missing == (7,)
    assert caught.excess is None
    assert "missing: (7)" in str(caught)
    assert "excess" not in str(caught)


def test_a_message_rides_in_the_reported_call():
    """The author's sentence needs no channel of its own.

    The reported call carries it, exactly as the engine's own Msg forms carry
    theirs.
    """
    caught = failure(
        lambda: testing.assert_answers([1], [2], msg="the edge counts must agree")
    )

    assert 'the edge counts must agree' in str(caught)
    assert caught.missing == (2,)


def test_a_query_answers_a_bag_three_ways(scratch_space):
    """Rows, one projected column, and plain Python values.

    A `Rows` iterates as ROWS, so each row compares as the expression of its
    values; `rows.y` projects the column, which is what a one-variable query
    usually wants. Neither is a special case of the other and both are here.
    """
    scratch_space.add(
        Expression([S.edge, S.a, S.b]),
        Expression([S.edge, S.a, S.c]),
    )
    rows = scratch_space.match(Expression([S.edge, S.a, V.y]))

    testing.assert_answers(rows.y, [S.c, S.b])
    testing.assert_answers(rows, [Expression([S.b]), Expression([S.c])])
    testing.assert_answers([1, "two"], ["two", 1])


def test_a_variable_of_the_same_name_is_one_answer_on_both_sides():
    """`$x` on each side is one variable, because both bags decode in ONE walk.

    That is what one MeTTa source writing the same two bags gets. Without the
    shared walk the engine's identity comparison would call two separately
    decoded `$x` different answers and this would fail.

    The reported bag is compared up to variable RENAMING, because a variable
    that has been through the engine carries a stack offset for a name rather
    than the one the caller wrote.
    """
    testing.assert_answers(
        [Expression([S.f, V.x])],
        [Expression([S.f, V.x])],
    )

    caught = failure(
        lambda: testing.assert_answers(
            [Expression([S.f, V.x])],
            [Expression([S.f, V.y])],
        )
    )
    assert len(caught.missing) == 1
    assert caught.missing[0].alpha_eq(Expression([S.f, V.y]))
    assert len(caught.excess) == 1
    assert caught.excess[0].alpha_eq(Expression([S.f, V.x]))
    # And the classifier survives the crossing at all, which it did not before
    # its parts were converted: this arrived as an EngineError saying the
    # classifier failed, for every assertion whose answers held a variable. The
    # reported call renders each variable on its own, so both read `$_0`; the
    # atoms that carry identity are .missing and .excess above.
    assert caught.actual == ["assert-answers", [["f", "$_0"]], [["f", "$_0"]]]


def test_the_first_line_of_a_test_file_can_be_an_assertion():
    """No MeTTa, no Space: the door starts the engine it needs.

    A FRESH interpreter, because this process booted one long ago and the
    check would be vacuous here. What it pins is the shape a reader writes
    first -- `testing.assert_answers(...)` with nothing constructed above it.
    """
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            'import metta.testing as testing\n'
            "testing.assert_answers([1, 2], [2, 1])\n"
            "from metta._errors.errors import AssertionFailure\n"
            "try:\n"
            "    testing.assert_includes([1], [2])\n"
            "except AssertionFailure as failure:\n"
            "    assert failure.missing == (2,), failure.missing\n"
            "    assert failure.excess is None\n"
            "else:\n"
            "    raise AssertionError('a false containment did not raise')\n",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr


def test_a_single_answer_is_refused_with_the_sequence_spelled_out():
    """One answer is [answer], and a str is the case that has to be loud.

    A str is iterable, so without the refusal a message passed by mistake
    would be compared character by character and reported as a bag of
    one-character answers.
    """
    for value in ("abc", S.a, 7):
        with pytest.raises(TypeError) as caught:
            testing.assert_answers(value, [])
        assert "sequence" in str(caught.value)
        assert caught.value.remedy.python.startswith("assert_answers(")
