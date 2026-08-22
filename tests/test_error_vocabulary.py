"""Purpose: pin the canonical error-atom vocabulary against the LeaTTa arbiter.
Assumes: the engine answers through the ordinary MeTTa surface; no probe needs
  a named space, a backend or a file.
Guarantees:
  - every member of the vocabulary answers the exact atom the arbiter answers,
    and an operand whose evaluation produced one finishes the enclosing call.
  [tested: test_the_error_vocabulary_answers_what_the_arbiter_answers; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
  - an under-applied operation answers a partial application and never takes
    the host process down.
  [tested: test_an_underapplied_operation_answers_instead_of_aborting; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
Fails when: a probe is read as a claim about Hyperon rather than about LeaTTa;
  the arbiter is LeaTTa and every pin below cites the LeaTTa file it came from.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import pytest

from petta import MeTTa

# The arbiter, file by file. Each pin below names the LeaTTa program whose
# MEASURED block carries the transcript this test asserts, all of them STATUS
# conforms against the pinned Hyperon 0.2.10 binary:
#
#   ai-brief-badargtype-multiplicity.md  the BadArgType cross product, ordered
#                                        arrow-major and actual-minor
#   stdlib.md:248-278                    BadArgType is (-> Number Type Type
#                                        ErrorDescription), BadType is
#                                        (-> Type Type ErrorDescription)
#   tests/semantics/control-stdlib/07_error.metta
#                                        a produced error emerges unchanged
#                                        through a call; a written one is data
#   tests/semantics/grounded/09-arity.metta
#                                        IncorrectNumberOfArguments
#   wiki/Hyperon-Divergences.md:44       (Error <culprit> StackOverflow)
#   wiki/Hyperon-Hacks-Register.md:51    Empty is removal, NotReducible is
#                                        "return the atom as is"; they differ


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one runnable's answers in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def test_the_error_vocabulary_answers_what_the_arbiter_answers() -> None:
    """Every member answers the atom the arbiter answers, in its exact shape."""
    metta = MeTTa()

    # BadArgType carries the position, the expected type and the actual one.
    assert _answers(metta, '!(+ 1 "s")') == [
        '(Error (+ 1 "s") (BadArgType 2 Number String))'
    ]
    # The upstream-inherited one-character string coercion is guarded, so a
    # one-character string is a String here exactly as it is there.
    assert _answers(metta, '!(+ 1 "8")') == [
        '(Error (+ 1 "8") (BadArgType 2 Number String))'
    ]

    # One error per rejected ACTUAL type and per declared ARROW: the full cross
    # product, outer loop over arrows in declaration order, inner loop over the
    # argument's actual types.
    metta.run("(: badargtype-a A)")
    metta.run("(: badargtype-g (-> C Number))")
    assert _answers(metta, "!(badargtype-g badargtype-a)") == [
        "(Error (badargtype-g badargtype-a) (BadArgType 1 C A))"
    ]
    metta.run("(: badargtype-a B)")
    assert _answers(metta, "!(badargtype-g badargtype-a)") == [
        "(Error (badargtype-g badargtype-a) (BadArgType 1 C A))",
        "(Error (badargtype-g badargtype-a) (BadArgType 1 C B))",
    ]
    metta.run("(: badargtype-g (-> D Number))")
    assert _answers(metta, "!(badargtype-g badargtype-a)") == [
        "(Error (badargtype-g badargtype-a) (BadArgType 1 C A))",
        "(Error (badargtype-g badargtype-a) (BadArgType 1 C B))",
        "(Error (badargtype-g badargtype-a) (BadArgType 1 D A))",
        "(Error (badargtype-g badargtype-a) (BadArgType 1 D B))",
    ]

    # BadType is the type-cast refusal and carries no position.
    assert _answers(metta, '!(type-cast "wrong" Number &self)') == [
        '(Error "wrong" BadType)'
    ]

    # IncorrectNumberOfArguments is a bare symbol.
    assert _answers(metta, "!(+ 1 2 3 4)") == [
        "(Error (+ 1 2 3 4) IncorrectNumberOfArguments)"
    ]
    assert _answers(metta, "!(and True True True)") == [
        "(Error (and True True True) IncorrectNumberOfArguments)"
    ]

    # StackOverflow reports the branch that ran out of fuel and keeps the
    # siblings that finished. The bound is SCOPED, because a bare
    # `(pragma! max-stack-depth 20)` sets one engine-wide setting that outlives
    # the MeTTa object that wrote it: max-stack-depth is a runner setting
    # rather than a per-module one [source: LeaTTa
    # MettaHyperonFull/Minimal/Interpreter.lean:891-894, which keys
    # interpreterModes by run context and deliberately does not key
    # maxStackDepth], and this engine holds one runner per process.
    overflow = MeTTa("&errorvocab-overflow")
    overflow.run("(= (vocab-spin $n) (vocab-spin (- $n 1)))")
    answers = _answers(
        overflow, "!(with-pragma! ((max-stack-depth 20)) (vocab-spin 5))"
    )
    assert len(answers) == 1
    assert answers[0].startswith("(Error ")
    assert answers[0].endswith(" StackOverflow)")

    # NotReducible is the third outcome, and this engine reports it as a status
    # beside the unreduced term rather than as an atom inside the answer.
    statuses = MeTTa("&errorvocab-status")
    statuses.run("(= (vocab-double $x) (* $x 2))")
    assert [kind for kind, _ in statuses.eval_status("(vocab-double 4)")] == [
        "value"
    ]
    assert [kind for kind, _ in statuses.eval_status("(VocabPoint 1 2)")] == [
        "not-reducible"
    ]

    # Empty is NOT the unit. It removes the branch; () is an ordinary value and
    # collapsing it yields a one-element expression holding it.
    assert _answers(metta, "!(collapse (empty))") == ["()"]
    assert _answers(metta, "!(collapse ())") == ["(())"]
    assert _answers(metta, "!(get-metatype ())") == ["Expression"]

    # An operand whose EVALUATION produced an error finishes the enclosing call
    # with that atom, unchanged, whatever the enclosing call would have done.
    metta.run("(: vocab-needs-number (-> Number Number))")
    metta.run("(= (vocab-needs-number $x) (+ $x 1))")
    metta.run("(= (vocab-untyped $x) (+ $x 1))")
    metta.run("(= (vocab-ignores $x) 5)")
    produced = '(Error (+ 1 "bad") (BadArgType 2 Number String))'
    for source in (
        '!(vocab-needs-number (+ 1 "bad"))',
        '!(vocab-untyped (+ 1 "bad"))',
        '!(vocab-ignores (+ 1 "bad"))',
        '!(== 4 (+ 1 "bad"))',
        '!(!= 4 (+ 1 "bad"))',
        '!(+ 1 (+ 1 "bad"))',
        '!(and True (+ 1 "bad"))',
    ):
        assert _answers(metta, source) == [produced], source

    # A condition that produced an error decides nothing, so if answers the
    # error rather than taking the else branch.
    assert _answers(metta, '!(if (< 1 "bad") yes no)') == [
        '(Error (< 1 "bad") (BadArgType 2 Number String))'
    ]
    assert _answers(metta, "!(if (> 3 1) yes no)") == ["yes"]

    # An operand WRITTEN as an error atom is data, and a declared parameter
    # reports it by position as an ErrorType argument.
    assert _answers(metta, "!(+ (Error source message) 1)") == [
        "(Error (+ (Error source message) 1) (BadArgType 1 Number ErrorType))"
    ]
    # Error's own two arguments stay syntactic and are not reduced.
    assert _answers(metta, "!(Error (+ 1 2) (+ 3 4))") == ["(Error (+ 1 2) (+ 3 4))"]
    # Assertions compare error atoms instead of propagating them, because their
    # operands are declared Atom and cross unevaluated.
    assert _answers(
        metta, "!(assertEqual (Error (+ 1 2) (+ 3 4)) (Error (+ 1 2) (+ 3 4)))"
    ) == ["True"]

    # The railway combinators observe an error instead of being short-circuited
    # by it, which is what makes the vocabulary usable from a program.
    assert _answers(metta, '!(if-error (vocab-needs-number (+ 1 "bad")) caught missed)') == [
        "caught"
    ]
    assert _answers(metta, "!(if-error ordinary caught missed)") == ["missed"]
    assert _answers(metta, "!(if-error (Error (+ 1 2) why) caught missed)") == [
        "caught"
    ]
    assert _answers(metta, "!(return-on-error 5 6)") == ["6"]
    assert _answers(metta, '!(return-on-error (vocab-needs-number (+ 1 "bad")) 6)') == [
        produced
    ]

    # A collapse keeps the error as an ordinary answer.
    assert _answers(metta, '!(collapse (+ 1 "bad"))') == [f"({produced})"]


# The nine registrations register_prolog_arities/1 used to make for a SWI
# system predicate of the same name. Each of these called the host predicate
# directly and aborted the runnable; the last three are controls that were
# always partial applications.
_UNDER_APPLIED = (
    "!(not)",
    "!(append)",
    "!(assert)",
    "!(exists_file)",
    "!(sleep)",
    "!(sqrt-math)",
    "!(get-metatype)",
    "!(min-atom)",
)


@pytest.mark.parametrize("source", _UNDER_APPLIED)
def test_an_underapplied_operation_answers_instead_of_aborting(source: str) -> None:
    """Too few arguments is an ordinary answer, never a host abort."""
    metta = MeTTa(f"&errorvocab-arity-{source.strip('!()').replace('-', '_')}")
    answers = _answers(metta, source)
    assert len(answers) == 1
    assert answers[0].startswith("(partial ")
