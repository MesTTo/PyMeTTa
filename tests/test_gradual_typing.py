"""Purpose: `%Undefined%` is the gradual type, and it is consistent with every
type in both directions, which is what decides whether an argument is admitted.
Guarantees:
  - a parameter declared %Undefined% admits any argument, and an argument
    whose type nothing declares satisfies any parameter, while an argument of
    a KNOWN and different type is refused [tested
    test_an_unknown_type_is_consistent_with_every_declared_type]
  - the rule reaches metatype parameters too, so Expression admits an
    undeclared symbol and refuses a number [tested
    test_the_gradual_rule_reaches_metatype_parameters]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from petta import MeTTa


@pytest.fixture()
def typed():
    """One engine carrying a parameter of each shape the rule distinguishes."""
    m = MeTTa()
    for form in (
        "(: concrete (-> Number Atom))",
        "(= (concrete $x) (got $x))",
        "(: unknown-param (-> %Undefined% Atom))",
        "(= (unknown-param $x) (got $x))",
        "(: declared-other OtherType)",
    ):
        m.run(form)
    return m


def _answers(m, query):
    """Every answer of `query`, as strings. Collapsed so a refusal reads as
    an empty list rather than as a missing group.
    """
    [[collapsed]] = m.run("!(collapse " + query + ")")
    return [str(a) for a in collapsed]


def test_an_unknown_type_is_consistent_with_every_declared_type(typed):
    """Gradual typing's consistency relation, Siek and Taha's `?`: the unknown
    type is consistent with every type and every type with it, so neither
    direction is a violation. This engine had BOTH directions backwards.

    Measured 2026-08-19 on hyperon 0.2.10 and on the LeaTTa mechanised
    interpreter, byte-identical across both: with
    `(: f2 (-> Number Number))`, `(f2 a)` and `(f2 (undeclared-call))` answer
    while `(f2 "s")` is a `BadArgType`, and with
    `(: g2 (-> %Undefined% Number))` both `(g2 1)` and `(g2 "s")` answer.
    """
    # A value of the declared type, and one whose type nothing declares.
    assert _answers(typed, "(concrete 1)") == ["(got 1)"]
    assert _answers(typed, "(concrete undeclared-symbol)") == [
        "(got undeclared-symbol)"
    ]
    assert _answers(typed, "(concrete (undeclared-call))") == [
        "(got (undeclared-call))"
    ]

    # A KNOWN and different type is still refused, which is the half that
    # makes the rule worth anything.
    # A KNOWN and wrong type is not the gradual case: it is reported, and the
    # arbiter reports it the same way [measured 2026-08-19: `!(concrete "s")`
    # answers `(Error (concrete "s") (BadArgType 1 Number String))` there].
    assert _answers(typed, '(concrete "s")') == [
        '(Error (concrete "s") (BadArgType 1 Number String))'
    ]
    assert _answers(typed, "(concrete declared-other)") == [
        "(Error (concrete declared-other) (BadArgType 1 Number OtherType))"
    ]

    # The other direction: an %Undefined% parameter admits everything.
    for argument in ("1", '"s"', "undeclared-symbol", "declared-other", "(1 2)"):
        assert _answers(typed, f"(unknown-param {argument})") == [
            f"(got {argument})"
        ], argument


def test_the_gradual_rule_reaches_metatype_parameters(typed):
    """A metatype parameter is decided by the same consistency relation before
    the structural check runs, so it admits a value whose type is unknown.

    Measured 2026-08-19 on both references, byte-identical:
    `(: meta-expr (-> Expression Atom))` gives `!(meta-expr foo)` =
    `(got foo)` and `!(meta-expr 7)` = `(BadArgType 1 Expression Number)`.
    """
    typed.run("(: takes-expr (-> Expression Atom))")
    typed.run("(= (takes-expr $e) (gote $e))")
    assert _answers(typed, "(takes-expr (1 2))") == ["(gote (1 2))"]
    assert _answers(typed, "(takes-expr undeclared-symbol)") == [
        "(gote undeclared-symbol)"
    ]
    assert _answers(typed, "(takes-expr 7)") == [
        "(Error (takes-expr 7) (BadArgType 1 Expression Number))"
    ]

    typed.run("(: takes-grounded (-> Grounded Atom))")
    typed.run("(= (takes-grounded $g) (gotg $g))")
    assert _answers(typed, "(takes-grounded 7)") == ["(gotg 7)"]
    assert _answers(typed, "(takes-grounded undeclared-symbol)") == [
        "(gotg undeclared-symbol)"
    ]
    assert _answers(typed, "(takes-grounded declared-other)") == [
        "(Error (takes-grounded declared-other) (BadArgType 1 Grounded OtherType))"
    ]


def test_a_declared_parameter_type_still_types_its_own_application(typed):
    """The %Undefined%-as-expected direction is what get-type reads on the
    function path, so fixing it also stops an application of a declared arrow
    from being typed element-wise.

    Before this, `(: tensor (-> %Undefined% DLTensor))` refused `1.0` against
    its own `%Undefined%` parameter and `!(get-type (tensor (1.0)))` answered
    `((-> %Undefined% DLTensor) (Number))`, the arrow beside its argument's
    type, rather than `DLTensor`.
    """
    typed.run("(: wraps (-> %Undefined% Wrapped))")
    for argument in ("1.0", "(1.0)", "undeclared-symbol", '"s"'):
        assert _answers(typed, f"(get-type (wraps {argument}))") == ["Wrapped"], argument
