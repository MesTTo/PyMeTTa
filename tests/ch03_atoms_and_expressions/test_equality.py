"""Purpose: `==` is TERM equality and answers a Bool for any two operands.
Guarantees:
  - a comparison across two different kinds answers False rather than
    refusing, and it never consults a type declaration [tested
    test_cross_kind_equality_answers_false]
  - `=alpha` remains the structural comparison beside it [tested
    test_alpha_equality_still_compares_across_kinds]
  - the integer 1 and the float 1.0 are NOT equal, because the comparison is
    on terms and not on numeric value [tested
    test_mixed_numeric_equality_is_term_equality]
  - an operand that is an Error atom is handed on rather than compared, which
    is a superset over upstream: there the inner call either fails its
    declared check or raises uncaught, so no comparison answers at all
    [tested test_an_error_operand_is_handed_on]
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


def test_cross_kind_equality_answers_false(declared):
    """Two operands of different kinds compare False; `==` asks no type
    question at all.

    Upstream's whole definition is `'=='(A,B,R) :- (A==B -> R=true ;
    R=false)` (PeTTa@ae66fa8 src/metta.pl:40-41), and its
    `(: == (-> $a $b Bool))` uses TWO independent type variables, so nothing
    constrains the pair. This engine refused these until 2026-08-30, through a
    comparable_operands/2 guard written for LeaTTa's one-variable declaration.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    for query in (
        '(== 1 "S")',
        "(== True 1)",
        "(== xnum ystr)",
        '(== xnum "s")',
        "(== xnum zbool)",
        '(== "s" 1)',
        "(== 1 a)",
        '(== a "a")',
        "(== xnum undeclared)",
        "(== 1 (undeclared-call))",
    ):
        assert _answer(declared, query) == ["False"], query

    assert _answer(declared, "(== xnum 1)") == ["False"]
    assert _answer(declared, "(== 1 1)") == ["True"]
    assert _answer(declared, '(== "S" "S")') == ["True"]
    assert _answer(declared, "(== true false)") == ["False"]

    # != is the same operator negated and carries the same rule.
    assert _answer(declared, '(!= 1 "S")') == ["True"]
    assert _answer(declared, "(!= 1 2)") == ["True"]
    assert _answer(declared, "(!= 1 1)") == ["False"]


def test_an_error_operand_is_handed_on(declared):
    """An Error atom is an evaluation that finished in error, not a value to
    compare, so it is handed on. The test runs only after `A == B` has missed,
    so two identical atoms, errors included, still compare True.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    answers = _answer(declared, '(== 4 (+ 1 "bad"))')
    assert len(answers) == 1
    assert answers[0].startswith("(Error (+ 1 ")


def test_mixed_numeric_equality_is_term_equality(declared):
    """The integer 1 and the float 1.0 are different TERMS, so they are not
    equal.

    Measured 2026-08-30 against upstream, byte-identical: `(== 1 1.0)` is
    False and `(!= 1 1.0)` is True there. This engine compared numbers by
    value with `=:=/2` until then, on LeaTTa's `Ground.equiv` promoting the
    integer with `Float.ofInt`.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    assert _answer(declared, "(== 1 1.0)") == ["False"]
    assert _answer(declared, "(== 1.0 1)") == ["False"]
    assert _answer(declared, "(!= 1 1.0)") == ["True"]
    assert _answer(declared, "(!= 1.0 1)") == ["True"]
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
