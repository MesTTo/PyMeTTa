"""Purpose: asking for a type is a question about an expression, not a reason
to run it.
Guarantees:
  - get-type and get-type-space leave their argument unevaluated, so an
    effectful operation named inside one does not fire [tested
    test_get_type_does_not_run_its_arguments_effects]
  - get-type answers a function application from its DECLARATION, which is
    what the arbiter answers [tested
    test_get_type_of_an_application_answers_the_declared_return_type]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import MeTTa


def _counting_engine():
    """An engine whose (petta-effectful) op records every call it gets."""
    m = MeTTa()
    fired: list[int] = []

    def effectful():
        fired.append(1)
        return 1

    m.register_op(effectful, name="petta-effectful")
    return m, fired


def test_get_type_does_not_run_its_arguments_effects():
    """Measured before this: the op FIRED, the counter went 0 to 1, and the
    answer was Number, the type of the value it returned. Every linter walk
    and every REPL inspection was invisibly effectful."""
    m, fired = _counting_engine()
    answer = m.run("!(get-type (petta-effectful))")
    assert fired == [], f"get-type ran its argument {len(fired)} time(s)"
    # Number was the old answer, and it could only come from the value the
    # op returned; nothing declares the expression itself.
    answers = [str(a) for group in answer for a in group]
    assert "Number" not in answers, answers

    m, fired = _counting_engine()
    m.run("!(get-type-space &self (petta-effectful))")
    assert fired == [], "get-type-space ran its argument"


def test_get_type_of_an_application_answers_the_declared_return_type():
    """LeaTTa's types-meta/20_atom_return_literal.metta, whose MEASURED block
    records `[Atom]` from both the mechanised interpreter and hyperon 0.2.10:
    the answer comes from the declaration, so it is the same whether or not
    the body would reduce."""
    m = MeTTa()
    m.run("(: literal-return (-> Number Atom))")
    m.run("(= (literal-return $x) (+ $x 1))")
    assert [str(a) for g in m.run("!(get-type (literal-return 2))") for a in g] == ["Atom"]
    # A value still types as itself, and an undeclared head is still undefined.
    assert [str(a) for g in m.run("!(get-type 1)") for a in g] == ["Number"]
    # A builtin application still types by its arrow rather than element-wise,
    # which is the same route that answers ErrorType for (Error Foo Boo).
    assert [str(a) for g in m.run("!(get-type (+ 1 2))") for a in g] == ["Number"]
    assert [str(a) for g in m.run("!(get-type (Error Foo Boo))") for a in g] == ["ErrorType"]
