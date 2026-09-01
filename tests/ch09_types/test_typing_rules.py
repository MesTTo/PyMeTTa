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
  - statically repeated parameter contracts yield to a later module-local
    typing rule, and removing the rule restores the discharged check
    [tested: test_a_static_parameter_proof_yields_to_a_later_typing_rule;
    commit=WORKTREE]
  - a static parameter proof requires every governing chain to prove the same
    checked type; gradual consistency and an inherited clause running under a
    different local declaration retain the runtime check
    [tested: test_a_consistent_chain_is_not_a_static_type_proof,
    test_an_inherited_clause_does_not_reuse_its_owners_parameter_proof;
    commit=WORKTREE]
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


#: The type vocabulary the differential below draws its pairs from: the two
#: wildcards, the widening pair, and three ordinary names that are none of
#: those. Every shipped ordinary and widening rule is exercised by some pair.
_TYPE_VOCABULARY = ["%Undefined%", "Atom", "Number", "String", "BigInt", "Bool"]


def _match_differential(metta, family="ordinary"):
    """Rows where the shipped fast path and the registry disagree.

    Asked of the engine directly, because the two relations being compared are
    engine-internal and the whole claim is that they agree. Every internal name
    carries a leading underscore: janus manages a named variable in a goal
    string as an INPUT, so `Rows` would arrive unbound and the goal would raise
    "Arguments are not sufficiently instantiated" before running.
    """
    goal = (
        f"space_module('{metta.name}', _Mod), "
        f"_Ts = {_TYPE_VOCABULARY!r}, ".replace("'", "'") +
        "findall(_L-_R2-_F-_G, "
        "  ( member(_L, _Ts), member(_R2, _Ts), "
        "    ( user:metta_shipped_types_match(_L, _R2) -> _F = yes ; _F = no ), "
        f"    ( type_rules:typing_rule_accepts(_Mod, {family}, _L, _R2) "
        "      -> _G = yes ; _G = no ) ), "
        "  _Rows), "
        "findall(_A-_B, ( member(_A-_B-_F2-_G2, _Rows), _F2 \\== _G2 ), _Bad), "
        "length(_Rows, _N), term_string(_N-_Bad, R)"
    )
    return metta.runtime.once(goal)["R"]


def test_the_shipped_fast_path_answers_what_the_registry_answers():
    """The shipped fast path answers what the registry answers.

    metta_types_match_in/3 reads the shipped rules inline rather than searching
    for them, and the two must agree. This is the engine's hottest type predicate: every typed argument of every
    typed call asks it. Reading it off the registry means backtracking over the
    family's entries and running the pattern machinery per entry, where the
    shipped answer is six inline comparisons. So the fast path exists, guarded
    on no user rule being able to override it, and this is the obligation that
    buys it: the same question put to both relations over every pair drawn from
    the vocabulary, and then again with a user rule registered, where the fast
    path must stand aside rather than answer.

    The cost it removes is not small. Replacing those comparisons with the
    registry search took a dependent-type backward chainer from 44,327,926
    inferences to 236,070,644 in one commit
    [measured 2026-08-30 at ecb213fc and its parent, on
    examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/04-nilbc.metta].
    """
    metta = MeTTa().self
    assert _match_differential(metta) == f"{len(_TYPE_VOCABULARY) ** 2}-[]"

    # A user rule that REFUSES a pair the shipped rules accept. The fast path
    # must stop answering, or the refusal would be inert.
    metta.run(
        "!(add-typing-rule! p38-refuses-number ordinary Number Number "
        "(refuse \"p38 refuses Number against Number\"))"
    )
    try:
        disagreements = _match_differential(metta)
        assert disagreements != f"{len(_TYPE_VOCABULARY) ** 2}-[]", (
            "with a user rule registered the fast path still answered, so the "
            "rule cannot change what a typed call accepts"
        )
        assert "'Number'-'Number'" in disagreements, disagreements
    finally:
        metta.run("!(remove-typing-rule! p38-refuses-number)")

    # Removal restores agreement, so the guard is a condition rather than a latch.
    assert _match_differential(metta) == f"{len(_TYPE_VOCABULARY) ** 2}-[]"


def test_a_static_parameter_proof_yields_to_a_later_typing_rule():
    """A later rule recompiles the proof away; removal restores it."""
    metta = MeTTa().self
    metta.run("(: P43PolicyPayload Type)")
    metta.run("(: p43-policy-value P43PolicyPayload)")
    metta.run(
        "(: p43-target (-> P43PolicyPayload P43PolicyPayload))"
    )
    metta.run("(= (p43-target $value) $value)")
    metta.run(
        "(: p43-policy-caller (-> P43PolicyPayload P43PolicyPayload))"
    )
    metta.run(
        "(= (p43-policy-caller $value) (p43-target $value))"
    )

    refusal = [
        "(Error (p43-policy-caller p43-policy-value) "
        "(BadArgType 1 P43PolicyPayload P43PolicyPayload "
        "(TypingRuleRefusal p43-deny-payload denied-after-compile)))"
    ]
    call = "(p43-policy-caller p43-policy-value)"
    assert _answers(metta, call) == ["p43-policy-value"]
    assert _answers(
        metta,
        "(add-typing-rule! p43-deny-payload ordinary "
        "P43PolicyPayload P43PolicyPayload (refuse denied-after-compile))",
    ) == ["True"]
    assert _answers(metta, call) == refusal
    assert _answers(metta, "(remove-typing-rule! p43-deny-payload)") == [
        "True"
    ]
    assert _answers(metta, call) == ["p43-policy-value"]


def test_a_rule_in_one_space_does_not_change_another_spaces_answers():
    """Policy invalidation and registry lookup remain space-local."""
    context = MeTTa()
    left = context.space("&p43-left")
    right = context.space("&p43-right")
    for space in (left, right):
        space.run("(: p43-local-target (-> Number Number))")
        space.run("(= (p43-local-target $value) $value)")

    left.run(
        "!(add-typing-rule! p43-left-denies-number ordinary Number Number "
        "(refuse left-space-only))"
    )
    assert _answers(left, "(p43-local-target 1)") == [
        "(Error (p43-local-target 1) "
        "(BadArgType 1 Number Number "
        "(TypingRuleRefusal p43-left-denies-number left-space-only)))"
    ]
    assert _answers(right, "(p43-local-target 1)") == ["1"]

    assert _answers(
        left, "(remove-typing-rule! p43-left-denies-number)"
    ) == ["True"]
    assert _answers(left, "(p43-local-target 1)") == ["1"]
    assert _answers(right, "(p43-local-target 1)") == ["1"]


def test_a_consistent_chain_is_not_a_static_type_proof():
    """One concrete chain cannot discharge a check for an unknown chain."""
    metta = MeTTa().self
    metta.run("(: P43Payload Type)")
    metta.run("(: p43-needs-payload (-> P43Payload P43Payload))")
    metta.run("(= (p43-needs-payload $value) $value)")
    metta.run("(: p43-multichain (-> P43Payload P43Payload))")
    metta.run("(: p43-multichain (-> %Undefined% P43Payload))")
    metta.run(
        "(= (p43-multichain $value) (p43-needs-payload $value))"
    )
    metta.run("(: p43-payload P43Payload)")
    metta.run("(: p43-string String)")

    assert _answers(metta, "(p43-multichain p43-payload)") == [
        "p43-payload"
    ]
    assert _answers(metta, "(p43-multichain p43-string)") == []


def test_an_inherited_clause_does_not_reuse_its_owners_parameter_proof():
    """A child declaration governs a call into an inherited equation."""
    context = MeTTa()
    parent = context.space("&p43-parent")
    child = context.space("&p43-child", inherits=parent)
    parent.run("(: P43Payload Type)")
    parent.run("(: p43-parent-target (-> P43Payload P43Payload))")
    parent.run("(= (p43-parent-target $value) $value)")
    parent.run("(: p43-parent-caller (-> P43Payload P43Payload))")
    parent.run(
        "(= (p43-parent-caller $value) (p43-parent-target $value))"
    )
    parent.run("(: p43-parent-value P43Payload)")
    child.run("(: p43-parent-caller (-> String String))")
    child.run("(: p43-child-value String)")

    assert _answers(parent, "(p43-parent-caller p43-parent-value)") == [
        "p43-parent-value"
    ]
    assert _answers(child, "(p43-parent-caller p43-child-value)") == []


def test_static_proofs_do_not_resurrect_the_types_nondet_branch():
    """The result check in upstream's types_nondet case still prunes."""
    metta = MeTTa().self
    metta.run("(: P43Type1 Type)")
    metta.run("(: P43Type2 Type)")
    metta.run("(: p43-nondet (-> P43Type1 P43Type1))")
    metta.run("(: p43-nondet (-> P43Type2 P43Type2))")
    metta.run(
        "(= (p43-nondet $value) "
        "   (if (== (get-type $value) P43Type1) p43-default $value))"
    )
    metta.run("(: p43-input P43Type1)")
    metta.run("(: p43-default P43Type2)")

    assert _answers(metta, "(p43-nondet p43-input)") == []


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
