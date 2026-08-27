"""Purpose: pin the sequence-variable surface, the variable's fifth face.
Guarantees:
  - ``...`` in a pattern child position is an anonymous segment and each
    occurrence is its own variable [tested
    test_ellipsis_is_an_anonymous_segment,
    test_two_ellipses_enumerate_every_split]
  - ``seg(V.rest)`` builds the named segment and its run projects through the
    answers doors as an Expression slice [tested test_seg_builds_a_named_segment,
    test_a_segment_binding_projects_as_an_expression_slice]
  - a compiled ``case`` star pattern lowers to the final-position fragment
    [tested test_a_case_star_pattern_binds_the_rest]
  - a star in a TEMPLATE stays Python's own splice [tested
    test_a_star_in_a_template_still_splices]
  - the ledger's parsing-by-unification exemplar enumerates its splits
    [tested test_solve_enumerates_every_split_around_a_separator]
  - an ask outside the three proved-finite fragments refuses and names the law
    [tested test_a_mixed_role_pattern_refuses_naming_the_law,
    test_the_commuting_equation_refuses_naming_kutsia]
  - every answered split re-unifies against the row it came from [tested
    test_every_answered_split_reunifies]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, Grounded, S, V, seg, solve
from metta.errors import MettaError

# The gap glyph the law grants and Python already spells. Kept as a value so a
# reader sees WHAT is being asserted rather than an Ellipsis literal buried in a
# tuple [source: ai-python-conventions.md 3.3, "MeTTa's own gap glyph IS
# Python's Ellipsis"].
GAP = ...


@pytest.fixture
def orders(metta):
    """Same-headed atoms of three different lengths in the shared space."""
    for atom in ((S.Order, 7, S.x, S.y), (S.Order, 8), (S.Order, 9, S.z), (S.Note, 1)):
        if not list(metta[atom]):
            metta += atom
    return metta


def test_ellipsis_is_an_anonymous_segment(orders):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert str(Expression((S.A, GAP, S.D))) == "(A ... D)"
    assert len(list(orders[(S.Order, GAP)])) == 3
    assert len(list(orders[(S.Note, GAP)])) == 1


def test_seg_builds_a_named_segment():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert str(seg(V.rest)) == "(:seg $rest)"
    with pytest.raises(TypeError, match="names a VARIABLE"):
        seg(S.rest)


def test_a_segment_binding_projects_as_an_expression_slice(orders):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    rows = {row.id: row.rest for row in orders[(S.Order, V.id, seg(V.rest))]}
    assert all(isinstance(rest, Expression) for rest in rows.values())
    assert rows == {
        Grounded(7): Expression((S.x, S.y)),
        Grounded(8): Expression(()),
        Grounded(9): Expression((S.z,)),
    }


def test_two_ellipses_enumerate_every_split():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Each `...` is its OWN variable, so the two gaps around SEP are free to
    # split the row wherever a SEP sits: the row below holds two, so the ask
    # answers twice.
    row = (S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    answers = solve((V.pre, GAP, S.SEP, GAP, V.post), row)
    assert len(list(answers)) == 2


def test_solve_enumerates_every_split_around_a_separator():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The ledger's own exemplar, section 9gg.1: "a gap pattern against a
    # sequence ENUMERATES its splits, because matching is nondeterministic;
    # list processing with no recursion written".
    row = (S.a, S.b, S.SEP, S.c, S.SEP, S.d)
    answers = solve((V.pre, GAP, S.SEP, GAP, V.post), row)
    assert [(row.pre, row.post) for row in answers] == [(S.a, S.d), (S.a, S.d)]


def test_a_case_star_pattern_binds_the_rest(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @metta.define
    def tail(order):
        match order:
            case (S.Order, id, *rest):
                return S.Kept(id, rest)
            case _:
                return S.Other

    assert list(tail(Expression((S.Order, 7, S.x, S.y)))) == [
        Expression((S.Kept, Grounded(7), Expression((S.x, S.y))))
    ]
    assert list(tail(Expression((S.Order, 8)))) == [
        Expression((S.Kept, Grounded(8), Expression(())))
    ]
    assert list(tail(Expression((S.Note, 1)))) == [S.Other]


def test_a_case_star_without_a_name_keeps_the_arm_anonymous(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @metta.define
    def headed(order):
        match order:
            case (S.Order, *_):
                return S.Headed
            case _:
                return S.Other

    assert list(headed(Expression((S.Order, 1, 2)))) == [S.Headed]
    assert list(headed(Expression((S.Note, 1)))) == [S.Other]


def test_a_star_in_a_template_still_splices():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Python's `*` ANALYZES in a pattern and SYNTHESIZES in a template, and the
    # template half is untouched: a starred call argument is still Python's own
    # unpacking at build time.
    parts = (S.x, S.y)
    assert S.Order(7, *parts) == Expression((S.Order, Grounded(7), S.x, S.y))


def test_a_mixed_role_pattern_refuses_naming_the_law(orders):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaError) as refusal:
        list(orders[(S.Order, seg(V.m), V.m)])
    message = str(refusal.value)
    assert "outside the proved finitary fragment" in message
    assert "mixed_roles" in message
    assert "SeqFragment.lean" in message


def test_the_commuting_equation_refuses_naming_kutsia(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Kutsia's own infinitary witness: X u = u X has the family X = u^n for
    # every n, so no complete finite answer set exists.
    with pytest.raises(MettaError) as refusal:
        metta.run("!(unify (f (:seg $x) a) (f a (:seg $x)) matched none)")
    message = str(refusal.value)
    assert "Theorem 62" in message
    assert "outside the proved finitary fragment" in message


def test_a_stored_marker_is_data_on_both_doors(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Which side a marker sits on decides what it means. STORED, it is the
    # symbol `...` and nothing else, so an ordinary variable matches it and an
    # ordinary pattern retrieves it; asked, the same glyph is a gap and consumes
    # it as one child [source: LeaTTa MettaHyperonFull/Core/SeqSyntax.lean,
    # parseConcreteAtom against parseSeqAtom].
    metta += (S.Marked, GAP, S.tail)
    assert [row.a for row in metta[(S.Marked, V.a, S.tail)]] == [S["..."]]
    assert len(list(metta[(S.Marked, GAP, S.tail)])) == 1


def test_a_repeated_named_segment_takes_the_same_run(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta += (S.RepeatPair, S.a, S.b, S.mid, S.a, S.b)
    metta += (S.RepeatPair, S.a, S.b, S.mid, S.c)
    matched = list(metta[(S.RepeatPair, seg(V.run), S.mid, seg(V.run))])
    assert len(matched) == 1
    assert matched[0].run == Expression((S.a, S.b))


@given(
    prefix=st.lists(st.sampled_from(["p", "q"]), max_size=4),
    suffix=st.lists(st.sampled_from(["r", "s"]), max_size=4),
)
def test_every_answered_split_reunifies(prefix, suffix):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The differential: whatever split the engine answers, putting the runs
    # back where the gaps stood has to rebuild the row it was given. This is
    # the property the enumeration exists to have, and it holds however the
    # separator falls among the parts.
    row = Expression(
        (S.row, *(S[name] for name in prefix), S.SEP, *(S[name] for name in suffix))
    )
    answers = solve((S.row, seg(V.pre), S.SEP, seg(V.post)), row)
    rebuilt = [
        Expression((S.row, *answer.pre, S.SEP, *answer.post)) for answer in answers
    ]
    assert rebuilt, f"no split answered for {row}"
    assert all(candidate == row for candidate in rebuilt)


@given(items=st.lists(st.sampled_from(["a", "b", "c"]), min_size=0, max_size=5))
def test_a_single_gap_takes_the_whole_run(items):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # One gap in final position is Kutsia's unitary fragment: exactly one
    # answer, and it is the whole remainder.
    row = Expression((S.row, *(S[name] for name in items)))
    answers = list(solve((S.row, seg(V.rest)), row))
    assert len(answers) == 1
    assert answers[0].rest == Expression(tuple(S[name] for name in items))
