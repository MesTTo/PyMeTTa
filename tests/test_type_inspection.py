"""Purpose: asking for a type is a question about an expression, not a reason
to run it.
Guarantees:
  - get-type and get-type-space leave their argument unevaluated, so an
    effectful operation named inside one does not fire [tested
    test_get_type_does_not_run_its_arguments_effects]
  - get-type answers a function application from its DECLARATION, which is
    what the arbiter answers [tested
    test_get_type_of_an_application_answers_the_declared_return_type]
  - an expression no arrow types reads element-wise, and the tuple it reads is
    %Undefined% as soon as one member's type is [tested
    test_one_untyped_component_makes_the_whole_expressions_type_undefined]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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
    and every REPL inspection was invisibly effectful.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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
    the body would reduce.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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


def test_one_untyped_component_makes_the_whole_expressions_type_undefined():
    """An expression no arrow types is read element-wise, and the tuple it
    reads is %Undefined% as soon as one member's type is: nothing is known
    about a tuple one of whose components is unknown, so reporting the shape
    while a hole sits inside it claims more than was derived.

    Measured 2026-08-19 on hyperon 0.2.10 and on the LeaTTa mechanised
    interpreter, byte-identical across both. Before this,
    `!(get-type (aa))` answered `(%Undefined%)`, a one-element tuple.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m = MeTTa()
    m.run("(: typed-sym Number)")

    def answer(query):
        return [str(a) for g in m.run("!" + query) for a in g]

    # Every member typed: the tuple stands, and nests.
    assert answer("(get-type (typed-sym))") == ["(Number)"]
    assert answer("(get-type (typed-sym typed-sym))") == ["(Number Number)"]
    assert answer("(get-type (1))") == ["(Number)"]
    assert answer("(get-type (typed-sym (typed-sym typed-sym)))") == [
        "(Number (Number Number))"
    ]

    # One member undeclared, in any position, and nothing is known.
    for hole in (
        "(get-type (aa))",
        "(get-type (aa bb))",
        "(get-type (typed-sym aa))",
        "(get-type (aa typed-sym))",
    ):
        assert answer(hole) == ["%Undefined%"], hole

    # The collapse is recursive because the walk is bottom-up: the inner
    # tuple is %Undefined% first, which makes the outer one %Undefined% too.
    assert answer("(get-type (typed-sym (typed-sym aa)))") == ["%Undefined%"]

    # A call whose head has equations but no declaration is the same shape,
    # and it is the one a program hits most.
    m.run("(= (nullary) 42)")
    assert answer("(get-type (nullary))") == ["%Undefined%"]
