"""Purpose: the acceptance criteria of the translator rule system, each checked
    by running a MeTTa program rather than by reading the registry. A rule
    declares its direction and a bidirectional one is a single declaration; a
    rule may decline with its own words; a rule may carry a cost and a
    conjunctive left side; and the protected core refuses to be replaced by a
    rewrite rule, with the name it refused in the message.
Assumes:
  - `sh run.sh FILE silent` prints one line per answer on stdout and puts an
    engine refusal on stderr, and the repository root is its working directory.
  - swipl is on PATH for the registry probes, which are run the way the other
    Prolog lanes are, from tests/prolog.
Guarantees:
  - every claim is read from a run of the engine. The direction test asserts
    that BOTH directions fire from one declaration and that no file in the
    tree writes the inverse; the refusal test asserts the rule's own words
    reach the output and that a declining rule leaves the call to ordinary
    dispatch; the cost test asserts the declared price changes which direction
    fires, on two inputs that differ only in size.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import subprocess
from pathlib import Path

PROTECTED_RULE = """(: if (-> Atom Atom Atom %Undefined%))
(= (if $c $t $e) (noeval (quote hijacked)))
!(add-translator-rule! if)
!(if True 1 2)
"""

UNPROTECTED_RULE = """(: once (-> Atom %Undefined%))
(= (once $e) (noeval (take 1 $e)))
!(add-translator-rule! once)
!(once (superpose (1 2 3)))
"""

# ONE declaration, and the inverse is never written down. The two sides have
# the same variables and differ in size, which is what lets the cost order
# send a small term one way and a large one the other.
BIDIRECTIONAL_RULE = """(: unpack (-> Atom %Undefined%))
(= (unpack (wrap (box $x))) (noeval (twin $x $x)))
!(add-translator-rule! unpack ((direction bidirectional)))
!(unpack (wrap (box 1)))
!(twin 1 1)
!(unpack (wrap (box (a b c))))
!(twin (a b c) (a b c))
!(get-atoms &self)
"""


# A rule that inspects its match and declines. The refused call falls through
# to the next equation, so the program still answers, and the words the rule
# used are readable afterwards.
REFUSING_RULE = """(: strength (-> Atom Atom %Undefined%))
(= (strength (dose $n) (unit mg))
   (if (> $n 1000)
       (refuse "a dose above 1000 is not a milligram strength")
       (noeval (mg $n))))
(= (strength (dose $n) (unit mg))
   (noeval (grams (/ $n 1000))))
!(add-translator-rule! strength)
!(strength (dose 250) (unit mg))
!(strength (dose 5000) (unit mg))
!(match &metta (translator-rule-refusal $rule $why) (refused $rule $why))
"""


# Two equivalent forms and one number deciding which the compiler emits. The
# same source is run twice, with the cost declaration and without it, and the
# two runs answer differently for the same call.
COST_RULE = """(: pow2 (-> Atom %Undefined%))
(= (pow2 $x) (noeval (mul $x $x)))
!(add-translator-rule! pow2 ((direction bidirectional){cost}))
!(pow2 3)
!(mul (a b c d e f g h i j) (a b c d e f g h i j))
"""

# Three patterns joined on two variables, which no single head could express.
CONJUNCTIVE_RULE = """(unit mass kg)
(unit length m)
(si kg kilogram)
(si m metre)

(: unit-of (-> Atom %Undefined%))
!(add-translator-rule! unit-of
   ((left ((unit-of $q) (unit $q $u) (si $u $s)))
    (right (in $s))))

!(unit-of mass)
!(unit-of length)
!(collapse (unit-of time))
!(match &self (= (unit-of $q) $body) (car-atom $body))
"""


# A rule whose right side invents a variable and says nothing about it. The
# exemption has to be a declaration, not a blanket skip, so this one still
# reports the precondition it fails.
UNDECLARED_EXTRA_VARIABLE = """(: p2b-invents (-> Atom %Undefined%))
(= (p2b-invents $x) (noeval (pair $x $y)))
!(add-translator-rule! p2b-invents)
"""


def _run_metta(repo_root: Path, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "run.sh", str(path), "silent"],
        capture_output=True,
        text=True,
        timeout=280,
        check=False,
        cwd=repo_root,
    )


def _answers(finished: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in finished.stdout.splitlines() if line.strip()]


def test_overriding_a_protected_name_is_refused_with_the_name(repo_root, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # A translator rule is consulted one line before the compiler's own special
    # forms, so without the refusal this program answers `(quote hijacked)`
    # and nothing anywhere says that `if` stopped meaning `if`.
    planted = tmp_path / "protected.metta"
    planted.write_text(PROTECTED_RULE)
    refused = _run_metta(repo_root, planted)

    assert refused.returncode != 0, refused.stdout
    assert "if" in refused.stderr
    assert "metta_protected_core" in refused.stderr
    assert "quote hijacked" not in refused.stdout

    # And the refusal is a REFUSAL, not a silent skip: the hijacking answer is
    # absent because the program stopped, not because the rule was ignored.
    assert "add-translator-rule!" in refused.stderr

    # An unprotected head the compiler also gives meaning to is still the
    # program's to take over. `once` is a special form AND ships as a rule in
    # lib/lib_derived.metta, so refusing it would refuse the engine's own work.
    allowed = tmp_path / "unprotected.metta"
    allowed.write_text(UNPROTECTED_RULE)
    accepted = _run_metta(repo_root, allowed)
    assert accepted.returncode == 0, accepted.stderr
    assert _answers(accepted)[-1] == "1"

    # What it took over is recorded rather than left to be discovered: the
    # register names the kind of meaning the head already had.
    probe = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "set_prolog_flag(argv, [backends]), consult('../../engine/metta.pl'), "
            "'add-translator-rule!'(once, _), "
            "forall(translator_rule_override(N, K), format('OVERRIDE ~w ~w~n', [N, K])), "
            "catch('add-translator-rule!'(collapse, _), "
            "      error(permission_error(register, metta_protected_core, Name), _), "
            "      format('REFUSED ~w~n', [Name]))",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "OVERRIDE once special_form" in probe.stdout
    assert "REFUSED collapse" in probe.stdout


def test_a_translator_rule_declares_its_direction_and_a_bidirectional_rule_is_one_declaration(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    planted = tmp_path / "bidirectional.metta"
    planted.write_text(BIDIRECTIONAL_RULE)
    finished = _run_metta(repo_root, planted)
    assert finished.returncode == 0, finished.stderr
    answers = _answers(finished)

    # ONE declaration, and both directions fire. Which one fires is decided per
    # call by the cost, so the same rule rewrites the small term forwards and
    # the large one backwards, and neither direction ever runs away.
    registration, forward, forward_normal, backward_normal, backward = answers[:5]
    assert registration == "True"
    assert forward == "(twin 1 1)"
    assert forward_normal == "(twin 1 1)"
    assert backward_normal == "(unpack (wrap (box (a b c))))"
    assert backward == "(unpack (wrap (box (a b c))))"

    # The inverse is the engine's own equation, sitting in the space beside the
    # one the author wrote. Nobody typed it.
    stored = "\n".join(answers[5:])
    assert "(= (unpack (wrap (box $_0))) (noeval (twin $_0 $_0)))" in stored
    assert "(= (twin $_0 $_0) (noeval (unpack (wrap (box $_0)))))" in stored
    assert "(direction bidirectional)" not in stored

    # And it is never hand-written anywhere in the tree either: no shipped
    # source spells an inverse beside its rule, which is the duplication the
    # declaration exists to remove.
    assert BIDIRECTIONAL_RULE.count("(= (twin") == 0

    # The registry holds the direction, and the derived row points back at the
    # rule it came from, which is what removal reads.
    probe = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "set_prolog_flag(argv, [backends]), consult('../../engine/metta.pl'), "
            "metta_host_set_silent(true), "
            f"load_metta_file('{planted}', _), "
            "forall(member(N, [unpack, twin]), "
            "       ( translator_rule(N, D), format('ROW ~w ~q~n', [N, D]) )), "
            "'remove-translator-rule!'(unpack, _), "
            "( translator_rule(twin, _) -> writeln('INVERSE KEPT') "
            "; writeln('INVERSE WITHDRAWN') ), "
            "( 'get-atoms'('&self', ['=', [twin|_], _]) -> writeln('EQUATION KEPT') "
            "; writeln('EQUATION WITHDRAWN') )",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "ROW unpack [direction(bidirectional)]" in probe.stdout
    assert "ROW twin [direction(inverse(unpack))]" in probe.stdout
    assert "INVERSE WITHDRAWN" in probe.stdout
    assert "EQUATION WITHDRAWN" in probe.stdout


def test_a_translator_rule_can_decline_with_its_own_words(repo_root, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    planted = tmp_path / "refusal.metta"
    planted.write_text(REFUSING_RULE)
    finished = _run_metta(repo_root, planted)
    assert finished.returncode == 0, finished.stderr
    registration, honoured, declined, recorded = _answers(finished)

    assert registration == "True"
    # The match the rule can honour is rewritten.
    assert honoured == "(mg 250)"
    # The one it declines is NOT rewritten by that equation, and the call
    # carries on to the next one rather than failing or raising.
    assert declined == "(grams 5)"
    # And the words are the rule's own, in the register a program can match.
    assert recorded == (
        '(refused strength "a dose above 1000 is not a milligram strength")'
    )

    # The refusal moves the rule set across the decidability line, and the
    # report says so instead of going on claiming the fragment it used to sit
    # in. A guard makes a peak unreachable, so a critical pair stops being a
    # decision and becomes an obligation.
    report = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "translator_confluence_main",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
            "--",
            str(planted),
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    ).stdout
    assert "can refuse, so it is CONDITIONAL" in report
    assert "undecidable in general" in report
    assert "conclusion: NOT DECIDED." in report
    assert "proof obligation" in report

    # An unguarded set still gets a decision, so the conditional verdict is a
    # property of the rules and not a blanket disclaimer.
    unguarded = tmp_path / "unguarded.metta"
    unguarded.write_text(UNPROTECTED_RULE)
    plain = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "translator_confluence_main",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
            "--",
            str(unguarded),
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    ).stdout
    assert "are UNCONDITIONAL" in plain
    assert "conclusion: NOT DECIDED." not in plain


def test_a_translator_rule_carries_a_cost_and_a_conjunctive_left_side(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    # A cost is expressible, and it DECIDES. The same two equivalent forms go
    # opposite ways depending on the one number the rule declares, which is
    # what an extractor does when it chooses between them.
    priced = tmp_path / "priced.metta"
    priced.write_text(COST_RULE.format(cost=" (cost 10)"))
    unpriced = tmp_path / "unpriced.metta"
    unpriced.write_text(COST_RULE.format(cost=""))

    with_cost = _answers(_run_metta(repo_root, priced))
    without_cost = _answers(_run_metta(repo_root, unpriced))

    big = "(a b c d e f g h i j)"
    # Priced at ten, `(pow2 3)` is the dearer form and gets expanded, while the
    # doubled big argument is the dearer one and gets collapsed.
    assert with_cost[1] == "(mul 3 3)"
    assert with_cost[2] == f"(pow2 {big})"
    # Unpriced, a head is one node like any other, so the small call collapses
    # instead of expanding. Same rule, same call, different answer.
    assert without_cost[1] == "(pow2 3)"
    assert without_cost[2] == f"(pow2 {big})"

    # A conjunctive left side: three patterns, joined on two variables, which
    # no single head could express.
    conjunctive = tmp_path / "conjunctive.metta"
    conjunctive.write_text(CONJUNCTIVE_RULE)
    joined = _answers(_run_metta(repo_root, conjunctive))
    registration, mass, length, missing, body_head = joined

    assert registration == "True"
    assert mass == "(in kilogram)"
    assert length == "(in metre)"
    # Conjuncts that do not match are a rule miss like any other: no answer.
    assert missing == "()"
    # And the join is the engine's own conjunctive query. The rule compiles to
    # the equation an author would have written by hand, with the conjuncts as
    # a `match` chain, so nothing here canonicalises variables, de-canonicalises
    # substitutions, tests them for compatibility or merges them the way an
    # e-graph implementation has to.
    assert body_head == "match"
    registry = (repo_root / "engine" / "translator_rules.pl").read_text()
    assert "conjunctive_body" in registry
    defined = {
        line.split("(")[0].split(" ")[0]
        for line in registry.splitlines()
        if line[:1].isalpha()
    }
    assert not defined & {"merge_subst", "decanonicalize", "compatible"}


def _confluence(repo_root: Path, files: list[Path]) -> str:
    command = [
        "swipl",
        "-q",
        "--on-error=status",
        "-g",
        "translator_confluence_main",
        "-t",
        "halt(0)",
        "translator_confluence.pl",
    ]
    if files:
        command += ["--"] + [str(f) for f in files]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    ).stdout


def test_the_shipped_translator_rules_bind_their_right_hand_variables(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    # Every rule the shipped libraries register either binds every variable it
    # writes on the right, or carries an exemption WITH A REASON. Read from
    # the rules themselves, so a rule added later is covered.
    survey = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "load_engine, "
            "forall(shipped_library(F), load_metta_file(F, _)), "
            "compile_time_rules('&self', _, _, Space, Prelude), "
            "append(Space, Prelude, Rules), "
            "forall(member(Rule, Rules), "
            "  ( Rule = (L ==> _), functor(L, N, _), "
            "    ( rhs_vars_in_lhs([Rule]) -> format('BOUND ~w~n', [N]) "
            "    ; translator_rule_extra_variables_exempt(N, Why) "
            "      -> format('EXEMPT ~w :: ~w~n', [N, Why]) "
            "    ; format('UNBOUND ~w~n', [N]) ) ))",
            "-t",
            "halt(0)",
            "translator_confluence.pl",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    ).stdout
    lines = [line for line in survey.splitlines() if line.strip()]
    assert lines, survey
    assert not [line for line in lines if line.startswith("UNBOUND")], survey

    # Not vacuous: the corpus contains both answers, and every exemption
    # carries words rather than a bare flag.
    exemptions = [line for line in lines if line.startswith("EXEMPT")]
    assert [line for line in lines if line.startswith("BOUND")]
    assert exemptions
    for exemption in exemptions:
        reason = exemption.split(" :: ", 1)[1]
        assert len(reason.split()) >= 5, exemption

    # The shipped set's termination line has moved, and the exemption it rests
    # on is printed with its reason rather than silently applied.
    report = _confluence(repo_root, [])
    termination = [
        line for line in report.splitlines() if line.startswith("termination:")
    ]
    assert len(termination) == 1, termination
    assert termination[0].startswith("termination: ESTABLISHED."), termination[0]
    assert "exempt from the extra-variables precondition: succeedsPredicate" in report
    assert "binders of the expansion" in report
    assert "conclusion: CONFLUENT." in report

    # The obstruction that remains is a DIFFERENT one on a different tier, and
    # the report names it rather than folding it into the line above. It is
    # the prelude's three identity rules, whose right side contains their left
    # so no path order can orient them; the compiler terminates on them
    # because `noeval` stops the expansion going round again, which the
    # first-order extraction does not model.
    assert "shipped tier:" in report
    assert "termination: NOT ESTABLISHED, no_rpo_order" in report

    # And the exemption is a DECLARATION, not a blanket skip: a rule that
    # invents a variable and says nothing still reports the precondition.
    planted = tmp_path / "invents.metta"
    planted.write_text(UNDECLARED_EXTRA_VARIABLE)
    undeclared = _confluence(repo_root, [planted])
    assert "termination: NOT ESTABLISHED. extra_variables" in undeclared
