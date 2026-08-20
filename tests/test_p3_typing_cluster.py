"""Purpose: exercise the public typing and policy contracts introduced by P3.
Guarantees:
  - all six dispatch axes are catalog-readable and patchable per function.
  [tested: test_every_dispatch_axis_is_readable_settable_and_defaulted; commit=WORKTREE]
  - type faults remain ordinary Error values that ``if-error`` can observe.
  [tested: test_an_argument_type_fault_is_a_value_a_program_can_catch; commit=WORKTREE]
  - DontEvalType declarations mask evaluation without relying on a type name.
  [tested: test_a_user_declared_lazy_type_receives_its_argument_unevaluated; commit=WORKTREE]
  - a duplicate declaration is refused with the existing row in the message.
  [tested: test_a_duplicate_declaration_names_the_first_one; commit=WORKTREE]
  - pragma! accepts only keys whose setting changes an engine mechanism.
  [tested: test_no_pragma_key_is_accepted_and_inert; commit=WORKTREE]
  - under-applied arrow heads have no type instead of a tuple fallback.
  [tested: test_an_underapplied_arrow_head_types_as_the_arbiter_does; commit=WORKTREE]
  - empty-expression type observers report unit without changing classifiers.
  [tested: test_the_empty_expressions_type_follows_the_arbiters_ruling; commit=WORKTREE]
"""

import pytest

from petta import MeTTa


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one query group's atoms in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def _set_dispatch_policy(
    metta: MeTTa, function: str, axis: str, value: str
) -> None:
    assert _answers(
        metta,
        f"!(add-atom &petta (dispatch-policy {function} {axis} {value}))",
    ) == ["()"]


def _remove_dispatch_policy(
    metta: MeTTa, function: str, axis: str, value: str
) -> None:
    assert _answers(
        metta,
        f"!(remove-atom &petta (dispatch-policy {function} {axis} {value}))",
    ) == ["()"]


def test_every_dispatch_axis_is_readable_settable_and_defaulted():
    metta = MeTTa(verbose=False)
    expected = {
        "(MismatchEnum MismatchOriginal)",
        "(NoMatchEnum NoMatchOriginal)",
        "(EvaluationOrderEnum OrderClause)",
        "(FunctionResultEnum Nondeterministic)",
        "(ClauseFailedEnum ClauseFailNonDet)",
        "(OutOfClausesEnum FailureOriginal)",
    }
    assert set(
        _answers(
            metta,
            "!(match &petta (dispatch-default $axis $value) ($axis $value))",
        )
    ) == expected

    alternates = {
        "MismatchEnum": "MismatchFail",
        "NoMatchEnum": "NoMatchFail",
        "EvaluationOrderEnum": "OrderFittest",
        "FunctionResultEnum": "Deterministic",
        "ClauseFailedEnum": "ClauseFailDet",
        "OutOfClausesEnum": "FailureEmpty",
    }
    for axis, value in alternates.items():
        _set_dispatch_policy(metta, "p31-readable", axis, value)
        assert _answers(
            metta,
            f"!(match &petta "
            f"(dispatch-policy p31-readable {axis} $value) $value)",
        ) == [value]
        _remove_dispatch_policy(metta, "p31-readable", axis, value)

    metta.run("(= (p31-only-a A) hit)")
    assert _answers(metta, "!(p31-only-a B)") == ["(p31-only-a B)"]
    _set_dispatch_policy(metta, "p31-only-a", "NoMatchEnum", "NoMatchFail")
    assert _answers(metta, "!(p31-only-a B)") == []
    _remove_dispatch_policy(metta, "p31-only-a", "NoMatchEnum", "NoMatchFail")

    metta.run("(= (p31-multi $x) first)")
    metta.run("(= (p31-multi $x) second)")
    assert _answers(metta, "!(p31-multi x)") == ["first", "second"]
    _set_dispatch_policy(
        metta, "p31-multi", "FunctionResultEnum", "Deterministic"
    )
    assert _answers(metta, "!(p31-multi x)") == ["first"]
    _remove_dispatch_policy(
        metta, "p31-multi", "FunctionResultEnum", "Deterministic"
    )

    metta.run("(= (p31-fails $x) (superpose ()))")
    assert _answers(metta, "!(p31-fails x)") == []
    _set_dispatch_policy(
        metta, "p31-fails", "OutOfClausesEnum", "FailureEmpty"
    )
    assert _answers(metta, "!(p31-fails x)") == ["()"]
    _remove_dispatch_policy(
        metta, "p31-fails", "OutOfClausesEnum", "FailureEmpty"
    )

    metta.run("(= (p31-clause $x) (superpose ()))")
    metta.run("(= (p31-clause $x) later)")
    assert _answers(metta, "!(p31-clause x)") == ["later"]
    _set_dispatch_policy(
        metta, "p31-clause", "ClauseFailedEnum", "ClauseFailDet"
    )
    assert _answers(metta, "!(p31-clause x)") == []
    _remove_dispatch_policy(
        metta, "p31-clause", "ClauseFailedEnum", "ClauseFailDet"
    )

    metta.run("(: p31-fit (-> Number Symbol))")
    metta.run("(= (p31-fit $x) number-branch)")
    metta.run("(: p31-fit (-> String Symbol))")
    metta.run("(= (p31-fit $x) string-branch)")
    assert _answers(metta, "!(p31-fit 1)") == [
        "number-branch",
        "string-branch",
    ]
    _set_dispatch_policy(
        metta, "p31-fit", "EvaluationOrderEnum", "OrderFittest"
    )
    assert _answers(metta, "!(p31-fit 1)") == ["number-branch"]
    assert _answers(metta, '!(p31-fit "x")') == ["string-branch"]
    _remove_dispatch_policy(
        metta, "p31-fit", "EvaluationOrderEnum", "OrderFittest"
    )

    metta.run("(: p31-number (-> Number Number))")
    metta.run("(= (p31-number $x) $x)")
    assert "BadArgType" in _answers(metta, '!(p31-number "x")')[0]
    _set_dispatch_policy(
        metta, "p31-number", "MismatchEnum", "MismatchFail"
    )
    assert _answers(metta, '!(p31-number "x")') == []
    _remove_dispatch_policy(
        metta, "p31-number", "MismatchEnum", "MismatchFail"
    )


def test_an_argument_type_fault_is_a_value_a_program_can_catch():
    metta = MeTTa(verbose=False)
    metta.run("(: p32-f (-> Number Number))")
    metta.run("(= (p32-f $x) $x)")

    assert _answers(metta, '!(if-error (p32-f "wrong") caught missed)') == [
        "caught"
    ]
    assert _answers(metta, "!(if-error (p32-f 1 2) caught missed)") == [
        "caught"
    ]
    assert _answers(
        metta, '!(if-error (type-cast "wrong" Number &self) caught missed)'
    ) == ["caught"]


def test_a_user_declared_lazy_type_receives_its_argument_unevaluated():
    metta = MeTTa(verbose=False)
    metta.run("(: OpaquePayload DontEvalType)")
    metta.run("(: inspect-opaque (-> OpaquePayload Symbol))")
    metta.run("(= (inspect-opaque $written) (get-metatype $written))")

    assert _answers(metta, "!(inspect-opaque (+ 1 2))") == ["Expression"]

    metta.run("(: LooksDontEval Type)")
    metta.run("(: inspect-eager (-> LooksDontEval Symbol))")
    metta.run("(= (inspect-eager $value) (get-metatype $value))")
    eager = _answers(metta, "!(inspect-eager (+ 1 2))")
    assert eager == [
        "(Error (inspect-eager (+ 1 2)) "
        "(BadArgType 1 LooksDontEval Number))"
    ]


def test_a_duplicate_declaration_names_the_first_one():
    metta = MeTTa(verbose=False)
    first = "(: duplicate-op (-> Number Number))"
    metta.run(first)

    def duplicate_op(value: int) -> int:
        return value

    with pytest.raises(Exception) as refused:
        metta.register_op(duplicate_op, name="duplicate-op")

    message = str(refused.value)
    assert "duplicate" in message
    assert "the first declaration is (: duplicate-op (-> Number Number))" in message
    assert _answers(metta, "!(duplicate-op 5)") == ["(duplicate-op 5)"]


def test_no_pragma_key_is_accepted_and_inert():
    metta = MeTTa(verbose=False)

    assert _answers(metta, "!(pragma! max-inferences 100000)") == ["()"]
    assert _answers(metta, "!(pragma! max-inferences none)") == ["()"]

    for key, value in (
        ("type-check", "auto"),
        ("max-stack-depth", "100"),
        ("interpreter", "bare-minimal"),
        ("unknown-policy", "on"),
    ):
        with pytest.raises(Exception, match=f"metta_pragma_key.*{key}"):
            metta.run(f"!(pragma! {key} {value})")


def test_an_underapplied_arrow_head_types_as_the_arbiter_does():
    metta = MeTTa(verbose=False)
    metta.run("(: Nil (List $t))")
    metta.run("(: Cons (-> $t (List $t) (List $t)))")

    assert _answers(metta, "!(get-type (Cons 1))") == []
    assert _answers(metta, "!(get-type (Cons 1 Nil))") == ["(List Number)"]


def test_the_empty_expressions_type_follows_the_arbiters_ruling():
    metta = MeTTa(verbose=False)
    metta.run("(: A Type)")
    metta.run("(: h (-> %Undefined% Atom))")
    metta.run("(: classifier-control (-> Number Atom))")
    metta.run("(= (classifier-control $x) accepted)")

    assert _answers(metta, "!(get-type ())") == ["(->)"]
    assert _answers(metta, "!(get-type-space &self ())") == ["(->)"]

    # These are the ruling case's five controls, in its recorded order.
    assert _answers(metta, "!(get-metatype ())") == ["Expression"]
    assert _answers(metta, "!(get-type (nop))") == ["(->)"]
    assert _answers(metta, "!(get-type assert)") == ["(-> Atom (->))"]
    assert _answers(metta, "!(is-function (->))") == ["True"]
    assert _answers(metta, "!(get-type (h ()))") == ["Atom"]

    # The observer type must not leak into argument classification. LeaTTa's
    # classifier derives no type here, so the existing gradual fallback admits
    # the value at a concrete parameter instead of rejecting unit against it.
    assert _answers(metta, "!(classifier-control ())") == ["accepted"]
