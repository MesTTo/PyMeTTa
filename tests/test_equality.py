"""Purpose: `==` compares two things of one type, and says so when it is
handed two of different types instead of answering a Bool that reads as a
verdict.
Guarantees:
  - a comparison across two KNOWN and different types ANSWERS its refusal,
    `(Error <call> (BadArgType <position> <expected> <actual>))`, while one
    whose either side has no declared type answers False [tested
    test_cross_kind_equality_answers_what_the_arbiter_answers]
  - `=alpha` stays the comparison that accepts anything, so the refusal has
    an escape hatch that is already in the language [tested
    test_alpha_equality_still_compares_across_kinds]
  - integer and float operands compare by numeric value, matching the
    arbiter's Ground.equiv promotion rule [tested
    test_mixed_numeric_equality_answers_what_the_arbiter_answers]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa


@pytest.fixture()
def declared():
    """One symbol of each kind a declaration can pin, so the rule can be
    exercised on symbols and not only on literals.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa().self
    for form in ("(: xnum Number)", "(: ystr String)", "(: zbool Bool)"):
        m.run(form)
    return m


def _answer(m, query):
    return [str(a) for g in m.run("!" + query) for a in g]


def test_cross_kind_equality_answers_what_the_arbiter_answers(declared):
    """Reproduced 2026-08-19: `!(== 1 "S")` answered `False`, which is also
    the answer for two Numbers that differ, so a conditional took the else
    branch and nothing said the question was meaningless.

    `==` is declared `(-> $a $a Bool)`, one type variable, so the two operands
    must have a consistent type. Measured 2026-08-19 on hyperon 0.2.10 and on
    the LeaTTa mechanised interpreter, byte-identical across both.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    # Both sides KNOWN and different: refused, and the refusal is an ANSWER
    # naming the position, the type the first operand fixed and the type the
    # second carries. The form after it still runs, which a raise took away.
    for query, expected, actual in (
        ('(== 1 "S")', "Number", "String"),
        ("(== True 1)", "Bool", "Number"),
        ("(== xnum ystr)", "Number", "String"),
        ('(== xnum "s")', "Number", "String"),
        ("(== xnum zbool)", "Number", "Bool"),
        ('(== "s" 1)', "String", "Number"),
    ):
        answers = _answer(declared, query)
        assert len(answers) == 1, query
        assert answers[0].startswith("(Error (=="), query
        assert f"(BadArgType 2 {expected} {actual})" in answers[0], query

    # One side with no declared type: nothing is contradicted, so the
    # comparison happens and answers False.
    for query in (
        "(== 1 a)",
        '(== a "a")',
        "(== xnum undeclared)",
        "(== 1 (undeclared-call))",
    ):
        assert _answer(declared, query) == ["False"], query

    # Same type, and the ordinary answers are untouched.
    assert _answer(declared, "(== xnum 1)") == ["False"]
    assert _answer(declared, "(== 1 1)") == ["True"]
    assert _answer(declared, '(== "S" "S")') == ["True"]
    assert _answer(declared, "(== true false)") == ["False"]

    # != is the same operator negated and carries the same rule.
    assert _answer(declared, '(!= 1 "S")') == [
        '(Error (!= 1 "S") (BadArgType 2 Number String))'
    ]
    assert _answer(declared, "(!= 1 2)") == ["True"]


def test_mixed_numeric_equality_answers_what_the_arbiter_answers(declared):
    """Mixed numeric equality answers what the arbiter answers.

    LeaTTa's `Ground.equiv` promotes the integer with `Float.ofInt` in
    both mixed numeric cases (`MettaHyperonFull/Core/Atom.lean:47-62`), and
    `Atom.equiv` uses that relation for grounded atoms (lines 110-116).
    """
    assert _answer(declared, "(== 1 1.0)") == ["True"]
    assert _answer(declared, "(== 1.0 1)") == ["True"]
    assert _answer(declared, "(!= 1 1.0)") == ["False"]
    assert _answer(declared, "(!= 1.0 1)") == ["False"]
    assert _answer(declared, "(== 1 1.5)") == ["False"]
    assert _answer(declared, "(!= 1.0 2)") == ["True"]


def test_an_expression_operand_is_left_alone(declared):
    """Expressions are the one axis the two references disagree on, so the
    guard does not touch them and the engine answers what it always did.

    Measured 2026-08-19: hyperon answers False for `(== () 1)`, `(== "s" ())`
    and `(== (1 2) (1 2 3))` while LeaTTa raises BadArgType for the first two;
    both answer False for `(== (1 2 3) ())` and `(== (1 2) (a b))`, which is
    the shape a MeTTa program writes. The collapse-and-compare idiom is what
    hangs on this, so it is checked directly.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert _answer(declared, "(== (collapse (superpose ())) ())") == ["True"]
    assert _answer(declared, "(== (collapse (superpose (1 2))) ())") == ["False"]
    for query in (
        "(== (1 2 3) ())",
        "(== (1 2) (a b))",
        "(== (1 2) (3 4))",
        "(== () 1)",
        '(== "s" ())',
        "(== (1 2) (1 2 3))",
    ):
        assert _answer(declared, query) == ["False"], query
    assert _answer(declared, "(== () ())") == ["True"]


def test_alpha_equality_still_compares_across_kinds(declared):
    """The refusal needs an escape hatch and the language already has one:
    `=alpha` is declared `(-> Atom Atom Bool)`, so it takes anything and
    compares structurally. Both references answer False for
    `!(=alpha 1 "S")`, measured 2026-08-19.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert _answer(declared, '(=alpha 1 "S")') == ["False"]
    assert _answer(declared, "(=alpha True 1)") == ["False"]
    assert _answer(declared, "(=alpha 1 1)") == ["True"]
