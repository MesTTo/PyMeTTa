"""Purpose: prove the public typing-rule registry changes typed calls and is
read by the shared rule-family overlap analyzer.
Guarantees:
  - a user refusal overrides an overlapping shipped acceptance, names its rule
    and reason in the Error value, and removal restores the shipped behavior
    [tested: test_a_user_typing_rule_participates_like_a_shipped_one;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the analyzer reports user/user and user/shipped intersections involving
    refusal or defer as conditional obligations
    [tested: test_a_user_typing_rule_participates_like_a_shipped_one;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the shipped reporting family keeps Atom ordinary while the runtime family
    retains Atom's gradual wildcard behavior
    [tested: test_shipped_reporting_rules_do_not_treat_atom_as_a_wildcard;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import subprocess

from metta import MeTTa


def _answers(metta: MeTTa, expression: str) -> list[str]:
    [[collapsed]] = metta.run(f"!(collapse {expression})")
    return [str(answer) for answer in collapsed]


def test_a_user_typing_rule_participates_like_a_shipped_one(repo_root, tmp_path):
    """The runtime and reporter both consume ``typing_rule_entry/7``.

    ``%Undefined%`` normally satisfies every expected type through the shipped
    gradual rule. The user refusal intersects that exact shipped rule, changes
    the call, and survives in the diagnostic by name. ``defer`` is also
    planted for the analyzer: it is a guarded/conditional rule, not a negative
    unconditional confluence result.
    """
    metta = MeTTa().self
    metta.run("(: p37-rule-target (-> P37Payload Atom))")
    metta.run("(= (p37-rule-target $value) (seen $value))")

    baseline = ["(seen p37-unknown)"]
    assert _answers(metta, "(p37-rule-target p37-unknown)") == baseline

    metta.run("(: p37-other P37Other)")
    mismatch = [
        "(Error (p37-rule-target p37-other) "
        "(BadArgType 1 P37Payload P37Other))"
    ]
    assert _answers(metta, "(p37-rule-target p37-other)") == mismatch
    assert _answers(
        metta,
        "(add-typing-rule! p37-accept ordinary P37Other P37Payload accept)",
    ) == ["True"]
    assert _answers(metta, "(p37-rule-target p37-other)") == [
        "(seen p37-other)"
    ]
    assert _answers(metta, "(remove-typing-rule! p37-accept)") == ["True"]
    assert _answers(metta, "(p37-rule-target p37-other)") == mismatch

    assert _answers(
        metta,
        "(add-typing-rule! p37-defer ordinary %Undefined% P37Payload defer)",
    ) == ["True"]
    assert _answers(metta, "(p37-rule-target p37-unknown)") == baseline
    assert _answers(metta, "(remove-typing-rule! p37-defer)") == ["True"]

    assert _answers(
        metta,
        "(add-typing-rule! p37-deny ordinary %Undefined% P37Payload "
        "(refuse denied-by-user))",
    ) == ["True"]
    assert _answers(metta, "(p37-rule-target p37-unknown)") == [
        "(Error (p37-rule-target p37-unknown) "
        "(BadArgType 1 P37Payload %Undefined% "
        "(TypingRuleRefusal p37-deny denied-by-user)))"
    ]

    assert _answers(metta, "(remove-typing-rule! p37-deny)") == ["True"]
    assert _answers(metta, "(p37-rule-target p37-unknown)") == baseline

    metta.run("(: p37-arity-target (-> Atom Atom Atom))")
    metta.run("(= (p37-arity-target $left $right) ($left $right))")
    assert _answers(metta, "(p37-arity-target left right)") == ["(left right)"]
    assert _answers(
        metta,
        "(add-typing-rule! p37-arity-deny arrow-arity 2 2 "
        "(refuse arity-denied-by-user))",
    ) == ["True"]
    assert _answers(metta, "(p37-arity-target left right)") == [
        "(Error (p37-arity-target left right) "
        "(TypingRuleRefusal p37-arity-deny arity-denied-by-user))"
    ]
    assert _answers(metta, "(remove-typing-rule! p37-arity-deny)") == ["True"]
    assert _answers(metta, "(p37-arity-target left right)") == ["(left right)"]

    planted = tmp_path / "typing-overlap.metta"
    planted.write_text(
        "!(add-typing-rule! p37-deny ordinary %Undefined% P37Payload "
        "(refuse denied-by-user))\n"
        "!(add-typing-rule! p37-guard ordinary %Undefined% $expected defer)\n"
    )
    completed = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "typing_confluence_main",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
            "--",
            str(planted),
        ],
        cwd=repo_root / "tests" / "prolog",
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
    )
    report = completed.stdout
    assert "user rule p37-deny" in report
    assert "user rule p37-guard" in report
    assert "shipped rule typing-ordinary-unknown-actual" in report
    assert "shipped rule typing-arrow-arity-exact" in report
    assert "shipped rule typing-bigint-widens-to-number" in report
    assert "shipped rule typing-metatype-expression" in report
    assert "CONDITIONAL OVERLAP (refusal)" in report
    assert "CONDITIONAL OVERLAP (guarded_defer)" in report
    assert "user rule p37-deny and user rule p37-guard" in report
    assert "user rule p37-deny and shipped rule " in report
    assert "unconditional critical-pair checker" in report


def test_shipped_reporting_rules_do_not_treat_atom_as_a_wildcard():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    metta = MeTTa().self
    metta.run("(: p37-r Type)")
    metta.run("(: p37-a Type)")
    metta.run("(: p37-value p37-a)")
    metta.run("(: p37-atom-result (-> p37-a Atom))")
    for metatype in ("Grounded", "Symbol", "Variable"):
        function = f"p37-needs-{metatype.lower()}"
        metta.run(f"(: {function} (-> {metatype} p37-r))")
        assert _answers(
            metta,
            f"(get-type ({function} (p37-atom-result p37-value)))",
        ) == []
