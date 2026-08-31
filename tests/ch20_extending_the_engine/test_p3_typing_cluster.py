"""Purpose: exercise the public typing and policy contracts introduced by P3.
Guarantees:
  - all six dispatch axes are catalog-readable and patchable per function.
  [tested: test_every_dispatch_axis_is_readable_settable_and_defaulted; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - type faults remain ordinary Error values that ``if-error`` can observe.
  [tested: test_an_argument_type_fault_is_a_value_a_program_can_catch; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - DontEvalType declarations mask evaluation without relying on a type name.
  [tested: test_a_user_declared_lazy_type_receives_its_argument_unevaluated; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a source duplicate is idempotent, operation registration refuses to adopt
    its existing row, and a duplicate public batch is rejected atomically.
  [tested: test_a_duplicate_declaration_names_the_first_one; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - pragma! validates bound values before a working setting can change,
    keeps the arbiter's HE spellings accepted and unenforced, and refuses
    only keys outside the closed registry.
  [tested: test_pragma_validates_values_and_refuses_only_unknown_keys; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - under-applied arrow heads have no type instead of a tuple fallback.
  [tested: test_an_underapplied_arrow_head_types_as_the_arbiter_does; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - empty-expression type observers report unit without changing classifiers.
  [tested: test_the_empty_expressions_type_follows_the_arbiters_ruling; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import MeTTa
from metta.errors import EngineError


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
        f"!(add-atom &metta (dispatch-policy {function} {axis} {value}))",
    ) == ["True"]


def _remove_dispatch_policy(
    metta: MeTTa, function: str, axis: str, value: str
) -> None:
    assert _answers(
        metta,
        f"!(remove-atom &metta (dispatch-policy {function} {axis} {value}))",
    ) == ["True"]


def test_every_dispatch_axis_is_readable_settable_and_defaulted():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
    # NoMatchFail, not NoMatchOriginal: a call whose heads all miss simply
    # fails, which is upstream's own answer for it -- it has no policy layer
    # at all, just `Goal =.. [Fun|CallArgs]` and a call
    # [source: PeTTa@ae66fa8 src/translator.pl:363-370]. The default moved
    # with the alignment, and it is what lets a covered call compile to the
    # direct Prolog goal instead of re-deciding clause selection above SWI's
    # own first-argument indexing.
    expected = {
        "(MismatchEnum MismatchOriginal)",
        "(NoMatchEnum NoMatchFail)",
        "(EvaluationOrderEnum OrderClause)",
        "(FunctionResultEnum Nondeterministic)",
        "(ClauseFailedEnum ClauseFailNonDet)",
        "(OutOfClausesEnum FailureOriginal)",
    }
    assert set(
        _answers(
            metta,
            "!(match &metta (dispatch-default $axis $value) ($axis $value))",
        )
    ) == expected

    alternates = {
        "MismatchEnum": "MismatchFail",
        "NoMatchEnum": "NoMatchOriginal",
        "EvaluationOrderEnum": "OrderFittest",
        "FunctionResultEnum": "Deterministic",
        "ClauseFailedEnum": "ClauseFailDet",
        "OutOfClausesEnum": "FailureEmpty",
    }
    for axis, value in alternates.items():
        _set_dispatch_policy(metta, "p31-readable", axis, value)
        assert _answers(
            metta,
            f"!(match &metta "
            f"(dispatch-policy p31-readable {axis} $value) $value)",
        ) == [value]
        _remove_dispatch_policy(metta, "p31-readable", axis, value)

    # The default direction, and the override, both round trips. A missed head
    # fails by default, which is what upstream answers for the same program
    # [measured 2026-08-30 against PeTTa@ae66fa8: `(= (only-a A) hit)` then
    # `!(only-a B)` prints a failed goal on both engines and
    # `!(collapse (only-a B))` answers `()` on both].
    metta.run("(= (p31-only-a A) hit)")
    assert _answers(metta, "!(p31-only-a B)") == []
    _set_dispatch_policy(metta, "p31-only-a", "NoMatchEnum", "NoMatchOriginal")
    assert _answers(metta, "!(p31-only-a B)") == ["(p31-only-a B)"]
    _remove_dispatch_policy(
        metta, "p31-only-a", "NoMatchEnum", "NoMatchOriginal"
    )
    assert _answers(metta, "!(p31-only-a B)") == []

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

    # The caller is compiled before the override. Changing catalog policy must
    # invalidate that static fast path, not only affect newly parsed queries.
    metta.run("(= (p31-precompiled) (p31-multi x))")
    assert _answers(metta, "!(p31-precompiled)") == ["first", "second"]
    _set_dispatch_policy(
        metta, "p31-multi", "FunctionResultEnum", "Deterministic"
    )
    assert _answers(metta, "!(p31-precompiled)") == ["first"]
    _remove_dispatch_policy(
        metta, "p31-multi", "FunctionResultEnum", "Deterministic"
    )
    assert _answers(metta, "!(p31-precompiled)") == ["first", "second"]

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


def test_an_argument_type_fault_is_a_value_a_program_can_catch():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
    metta.run("(: p32-f (-> Number Number))")
    metta.run("(= (p32-f $x) $x)")

    assert _answers(metta, '!(p32-f "wrong")') == [
        '(Error (p32-f "wrong") (BadArgType 1 Number String))'
    ]
    # Too many arguments RAISE rather than answering, and the raise names the
    # arities p32-f has beside the one this call asked for
    # [measured 2026-08-30 against PeTTa@ae66fa8].
    assert _answers(metta, "!(repr (catch (p32-f 1 2)))") == [
        '"(Error (domain_error (function_input_arities p32-f (1)) 2) none)"'
    ]
    assert _answers(metta, '!(type-cast "wrong" Number &self)') == [
        '(Error "wrong" BadType)'
    ]

    assert _answers(metta, '!(if-error (p32-f "wrong") caught missed)') == [
        "caught"
    ]
    # An arity fault is NOT one of those values: it raises, so if-error never
    # sees an Error to test and the ball travels past it, which is what
    # upstream does with the same three forms
    # [measured 2026-08-30 against PeTTa@ae66fa8]. `catch` is the form that
    # turns it into a value, as the repr assertion above shows.
    with pytest.raises(EngineError, match="function_input_arities"):
        _answers(metta, "!(if-error (p32-f 1 2) caught missed)")
    assert _answers(
        metta, '!(if-error (type-cast "wrong" Number &self) caught missed)'
    ) == ["caught"]


def test_a_user_declared_lazy_type_receives_its_argument_unevaluated():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
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

    # Both the callee and its caller exist before the marker declaration. The
    # type-marker dependency must rebuild the stored caller, not merely change
    # calls compiled after the declaration.
    metta.run("(: LatePayload Type)")
    metta.run("(: inspect-late (-> LatePayload Symbol))")
    metta.run("(= (inspect-late $value) (get-metatype $value))")
    metta.run("(= (late-inspection) (inspect-late (+ 1 2)))")
    assert "BadArgType" in _answers(metta, "!(late-inspection)")[0]
    assert "BadArgType" in _answers(metta, "!(inspect-late (+ 1 2))")[0]
    metta.run("(: LatePayload DontEvalType)")
    assert _answers(metta, "!(late-inspection)") == ["Expression"]
    assert _answers(metta, "!(inspect-late (+ 1 2))") == ["Expression"]
    assert _answers(
        metta, "!(remove-atom &self (: LatePayload DontEvalType))"
    ) == ["True"]
    assert "BadArgType" in _answers(metta, "!(late-inspection)")[0]
    assert "BadArgType" in _answers(metta, "!(inspect-late (+ 1 2))")[0]


def test_a_duplicate_declaration_names_the_first_one():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
    first = "(: duplicate-op (-> Number Number))"
    metta.run(first)
    metta.run(first)
    assert _answers(metta, "!(match &self (: duplicate-op $type) $type)") == [
        "(-> Number Number)"
    ]

    def duplicate_op(value: int) -> int:
        return value

    with pytest.raises(Exception) as refused:
        metta.op(duplicate_op, name="duplicate-op", effect="pureStructural")

    message = str(refused.value)
    assert "duplicate" in message
    assert "the first declaration is (: duplicate-op (-> Number Number))" in message
    assert _answers(metta, "!(duplicate-op 5)") == ["(duplicate-op 5)"]

    batch = metta.parse("(: duplicate-in-batch (-> Number Number))")
    with pytest.raises(Exception) as batch_refused:
        metta.add(batch, batch)

    batch_message = str(batch_refused.value)
    assert "duplicate" in batch_message
    assert (
        "the first declaration is "
        "(: duplicate-in-batch (-> Number Number))" in batch_message
    )
    assert _answers(
        metta,
        "!(match &self (: duplicate-in-batch $type) $type)",
    ) == []


def test_pragma_validates_values_and_refuses_only_unknown_keys():
    """The merged registry doctrine, pinned from the host side.

    The bounds validate their values before a working setting can be replaced, the arbiter's HE spellings stay
    accepted and unenforced, max-stack-depth answers its error as an atom,
    and only a key outside the closed registry is a hard refusal.
    """
    metta = MeTTa(verbose=False).self

    assert _answers(metta, "!(pragma! max-time 0.25)") == ["()"]
    assert _answers(metta, "!(pragma! max-time none)") == ["()"]
    assert _answers(metta, "!(pragma! max-inferences 100000)") == ["()"]
    assert _answers(metta, "!(pragma! max-inferences none)") == ["()"]

    for key, bad_value in (
        ("max-time", "not-a-number"),
        ("max-time", "0"),
        ("max-time", "-1"),
        ("max-inferences", "not-a-number"),
        ("max-inferences", "0"),
        ("max-inferences", "-1"),
        ("max-inferences", "1.5"),
    ):
        with pytest.raises(
            Exception,
            match=rf"metta_pragma_value.*{key}",
        ):
            metta.run(f"!(pragma! {key} {bad_value})")

    try:
        assert _answers(metta, "!(pragma! type-check auto)") == ["()"]
        assert _answers(metta, "!(pragma! interpreter bare-minimal)") == ["()"]
        assert _answers(metta, "!(pragma! max-stack-depth 100)") == ["()"]
        assert _answers(metta, "!(pragma! max-stack-depth -3)") == [
            "(Error (pragma! max-stack-depth -3) UnsignedIntegerIsExpected)"
        ]

        with pytest.raises(Exception, match=r"metta_pragma_key.*unknown-policy"):
            metta.run("!(pragma! unknown-policy on)")
    finally:
        # A pragma is ONE engine-wide setting rather than a property of this
        # MeTTa object, so the three settings above outlive it and bound every
        # later evaluation in the process. `max-stack-depth 100` left set is a
        # StackOverflow in whichever test runs next.
        for key in ("type-check", "interpreter", "max-stack-depth"):
            metta.run(f"!(pragma! {key} none)")


def test_an_underapplied_arrow_head_types_as_the_arbiter_does():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
    metta.run("(: Nil (List $t))")
    metta.run("(: Cons (-> $t (List $t) (List $t)))")

    assert _answers(metta, "!(get-type (Cons 1))") == []
    assert _answers(metta, "!(get-type (Cons 1 Nil))") == ["(List Number)"]


def test_the_empty_expressions_type_follows_the_arbiters_ruling():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa(verbose=False).self
    metta.run("(: A Type)")
    metta.run("(: h (-> %Undefined% Atom))")
    metta.run("(: classifier-control (-> Number Atom))")
    metta.run("(= (classifier-control $x) accepted)")

    assert _answers(metta, "!(get-type ())") == ["(->)"]
    assert _answers(metta, "!(get-type-space &self ())") == ["(->)"]

    for observer in ("get-type", "get-type-space &self"):
        answer = _answers(metta, f"!({observer} $subject)")
        assert len(answer) == 1
        assert answer[0].startswith("$"), answer

    # These are the ruling case's five controls, in its recorded order.
    assert _answers(metta, "!(get-metatype ())") == ["Expression"]
    assert _answers(metta, "!(get-type (nop))") == ["(->)"]
    assert _answers(metta, "!(get-type assert)") == ["(-> %Undefined% (->))"]
    assert _answers(metta, "!(is-function (->))") == ["True"]
    assert _answers(metta, "!(get-type (h ()))") == ["Atom"]

    # The observer type must not leak into argument classification. LeaTTa's
    # classifier derives no type here, so the existing gradual fallback admits
    # the value at a concrete parameter instead of rejecting unit against it.
    assert _answers(metta, "!(classifier-control ())") == ["accepted"]
