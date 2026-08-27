"""Purpose: the three acceptance criteria of the metatheory cluster, each
    checked against behaviour rather than against prose.
    WHAT IT COVERS: REWRITING for confluence and NARROWING for termination,
    which are different relations over the same rule set and are kept apart
    everywhere below. Critical pairs are a rewriting notion, and they reach
    this rule set because a rule is MATCHED against its call: the rule runs on
    a copy of the arguments and the match is re-checked with subsumes_term/2,
    so a rule that instantiated the call is rejected rather than committed.
    Termination is asked of a wider set, one closed over the equations the
    rule bodies reach, and a body is EVALUATED while the program compiles,
    which narrows; so the termination reports come from engine/narrowing.pl's
    reduction rather than from engine/trs.pl's order directly.
    The confluence checker is an ADAPTATION whose provenance and whose
    termination caveat are both recorded and both true; the compile-time rule
    set's termination is ESTABLISHED or the failure is NAMED, with no third
    answer; and two translator rules that overlap are REPORTED with the overlap
    named rather than silently ordered.
Assumes:
  - swipl is on PATH and the working directory conventions of the Prolog lanes
    hold: tests/prolog/translator_confluence.pl is run from tests/prolog.
  - a MeTTa file written into a temporary directory can be loaded by path, and
    `sh run.sh FILE silent` prints one line per answer and nothing else
    [measured 2026-08-19].
Guarantees:
  - the provenance test does not stop at the header text: it RUNS the
    counter-example the header names and observes both halves of the caveat,
    the loop and the normal form the loop misses.
  - the termination test walks every MeTTa file this tree ships that registers
    a translator rule, so "no third answer" is a claim about the shipped
    corpus and not about one example.
  - the overlap test proves the thing the report warns about, by running the
    same two rules in both orders and getting two different answers.
  - a rule's body is its condition: a body with no answer declines and the next
    clause is tried, a rule whose only clause declines leaves the call to
    ordinary dispatch, and the report says which of its verdict is a decision
    and which a proof obligation because of it
    [tested: test_an_answerless_translator_rule_body_behaves_as_ruled;
     commit=4465fc492071932eab0b2818a4ccd46f01f0d6aa]
  - every file that names the rewriting machinery says which of narrowing and
    rewriting its own results are about, and a file that starts naming it and
    says nothing fails the discovery half rather than passing quietly
    [tested: test_each_narrowing_citation_in_the_plan_states_which_it_covers;
    commit=6bacf853c74cc01304ffc2bae038ff60e3309e16]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

# Every reason engine/narrowing.pl can give for not establishing termination. A
# reason outside this set would mean the analysis grew an answer nobody wrote
# down, which is the third state this item exists to forbid.
NAMED_FAILURES = frozenset(
    {
        "not_left_linear",
        "extra_variables",
        "symbol_at_two_arities",
        "not_constructor_system",
        "unknown_entry",
        "no_safe_filtering",
        "no_rpo_order",
    }
)

OVERLAPPING_RULES = """(= (m2 a) (noeval one))
(= (m2 $x) (noeval two))
!(add-translator-rule! m2)
(= (usem2) (m2 a))
!(usem2)
"""

REVERSED_RULES = """(= (m2 $x) (noeval two))
(= (m2 a) (noeval one))
!(add-translator-rule! m2)
(= (usem2) (m2 a))
!(usem2)
"""

CLEAN_RULES = """(= (m7 $x) (noeval (cons 5 $x)))
!(add-translator-rule! m7)
(= (usem7) (m7 (6)))
!(usem7)
"""

# A rule's body is its condition. `(empty)` is the policy-free way to write a
# body with no answer: no dispatch declaration is involved, so what these
# measure is the rule machinery and not a NoMatch setting.
ANSWERLESS_BODY_FALLS_THROUGH = """(= (m5 a) (empty))
(= (m5 $x) (noeval two))
!(add-translator-rule! m5)
(= (usem5) (m5 a))
!(usem5)
"""

ANSWERLESS_BODY_ALONE_DECLINES = """(= (m6 a) (empty))
!(add-translator-rule! m6)
(= (usem6) (m6 a))
!(collapse (usem6))
"""

# The same two equations with no rule registered, so the difference between a
# rule and a function is measured rather than assumed.
ANSWERLESS_BODY_AS_A_FUNCTION = """(= (fn5 a) (empty))
(= (fn5 $x) two)
!(collapse (fn5 a))
"""


def _confluence_report(repo_root: Path, files: list[Path]) -> str:
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
    finished = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    return finished.stdout


def _run_metta(repo_root: Path, path: Path) -> list[str]:
    finished = subprocess.run(
        ["sh", "run.sh", str(path), "silent"],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root,
    )
    return [line for line in finished.stdout.splitlines() if line.strip()]


def _unwrapped(path: Path) -> str:
    """A Prolog file's prose with comment markers and line breaks taken out.

    A header claim that happens to be wrapped across two lines is still one
    claim, and a test that reads it should not go red when someone reflows the
    paragraph around it.
    """
    stripped = (line.lstrip("%").strip() for line in path.read_text().splitlines())
    return " ".join(" ".join(stripped).split())


def _termination_line(report: str) -> str:
    lines = [line for line in report.splitlines() if line.startswith("termination:")]
    assert len(lines) == 1, f"expected one termination line, got {lines}"
    return lines[0]


def test_the_confluence_checker_records_its_provenance_and_its_termination_caveat(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root,
):
    checker = _unwrapped(repo_root / "engine" / "trs.pl")

    # An adaptation says whose work it adapts, under what terms, and what the
    # port changed. Without the last one the header is a courtesy rather than
    # something a reader can check the file against.
    assert "Markus Triska" in checker
    assert "PUBLIC DOMAIN" in checker
    assert "https://www.metalevel.at/trs/trs.pl" in checker
    assert "library(clpz) becomes library(clpfd)" in checker

    # The original's own honesty about normal_form/3, kept word for word, with
    # the counter-example it names.
    assert "May not terminate!" in checker
    assert "a ==> a, f(X) ==> b" in checker

    # And the caveat is TRUE, both halves of it. The reduction loops, and the
    # term it loops on does have a normal form, which is what makes this a
    # documented limit rather than a defect report.
    finished = subprocess.run(
        [
            "swipl",
            "-q",
            "-g",
            "use_module('../../engine/trs.pl'), "
            "call_with_inference_limit("
            "  normal_form([a ==> a, f(_) ==> b], f(a), _), 100000, Limit), "
            "format('LOOP ~w~n', [Limit]), "
            "step([f(_) ==> b, a ==> a], f(a), T), format('NORMAL ~w~n', [T])",
            "-t",
            "halt",
        ],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
    )
    assert "LOOP inference_limit_exceeded" in finished.stdout
    assert "NORMAL b" in finished.stdout


def _translator_rule_files(repo_root: Path) -> list[Path]:
    """Every shipped MeTTa file that REGISTERS a translator rule.

    The marker is the runnable form rather than the bare name, because
    lib/lib_builtin_types/lib_builtin_types.metta declares the builtin's type and registers
    nothing, and a report over it would have no rule set to analyse.
    """
    roots = [repo_root / "examples", repo_root / "lib"]
    found = [
        path
        for root in roots
        for path in sorted(root.rglob("*.metta"))
        if "!(add-translator-rule!" in path.read_text()
    ]
    assert found, "no shipped MeTTa file registers a translator rule"
    return found


def test_the_compile_time_rule_set_is_shown_terminating_or_the_failure_is_named(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root,
):
    # The shipped libraries, then every shipped file that registers a rule, one
    # at a time so a failure names the file that caused it.
    reports = [_confluence_report(repo_root, [])]
    reports += [
        _confluence_report(repo_root, [path])
        for path in _translator_rule_files(repo_root)
    ]

    outcomes = [_termination_line(report) for report in reports]
    for outcome in outcomes:
        if outcome.startswith("termination: ESTABLISHED."):
            continue
        assert outcome.startswith("termination: NOT ESTABLISHED. "), outcome
        # The reason's own name, ahead of whatever argument or entry the line
        # goes on to give.
        reason = outcome[len("termination: NOT ESTABLISHED. ") :]
        name = reason.split("(")[0].split()[0].rstrip(",")
        assert name in NAMED_FAILURES, f"unnamed failure {reason!r}"

    # Not vacuous: the shipped corpus contains both answers, so neither branch
    # of the criterion is untested by it.
    assert any(o.startswith("termination: ESTABLISHED.") for o in outcomes)
    assert any(o.startswith("termination: NOT ESTABLISHED.") for o in outcomes)


def test_the_established_route_names_what_decided_it(repo_root, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    planted = tmp_path / "clean.metta"
    planted.write_text(CLEAN_RULES)
    report = _confluence_report(repo_root, [planted])
    assert _termination_line(report).startswith("termination: ESTABLISHED.")
    assert "argument filtering transformation" in report
    assert "recursive path order" in report
    assert "filtering: " in report
    assert "precedence, lowest first: " in report


def test_overlapping_translator_rules_are_reported_with_the_overlap_named(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    planted = tmp_path / "overlap.metta"
    planted.write_text(OVERLAPPING_RULES)
    report = _confluence_report(repo_root, [planted])

    # Named: which two rules, where they overlap, and what each of them gives.
    assert "OVERLAP counterexample: rule 1 (m2 a) and rule 2 (m2 $" in report
    assert "at position []" in report
    assert "rule 1 gives (noeval one)" in report
    assert "rule 2 gives (noeval two)" in report
    assert "conclusion: NOT LOCALLY CONFLUENT." in report

    # The fragment, and which side of it this rule set is on. Settled
    # 2026-08-21: a rule's body is its condition, so every rule is a
    # conditional rewrite rule and the verdict this report decides is about
    # the unconditional system it extracts from the heads.
    assert "Knuth and Bendix (1970)" in report
    assert "every translator rule is a CONDITIONAL rewrite rule" in report
    assert "a rule's BODY is its condition" in report
    assert "undecidable in general" in report
    assert "UNCONDITIONAL system extracted from the rule heads" in report
    assert "PROOF OBLIGATION" in report

    # And the thing the report warns about is real: the same two rules in the
    # other order make the engine answer differently.
    reversed_file = tmp_path / "reversed.metta"
    reversed_file.write_text(REVERSED_RULES)
    assert _run_metta(repo_root, planted)[-1] == "one"
    assert _run_metta(repo_root, reversed_file)[-1] == "two"


def test_a_rule_set_without_an_overlap_is_reported_as_having_none(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path
):
    planted = tmp_path / "clean.metta"
    planted.write_text(CLEAN_RULES)
    report = _confluence_report(repo_root, [planted])
    assert "OVERLAP" not in report
    assert "0 divergent" in report
    assert "conclusion: CONFLUENT." in report


def test_the_detector_is_run_against_its_own_planted_rule_sets(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    finished = subprocess.run(
        [
            "swipl",
            "-q",
            "--on-error=status",
            "-g",
            "translator_confluence_selftest",
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
    assert "each on the side its shape predicts" in finished.stdout


@pytest.mark.parametrize(
    "source, expected",
    [
        (OVERLAPPING_RULES, "one"),
        (REVERSED_RULES, "two"),
    ],
)
def test_assertion_order_alone_decides_which_overlapping_rule_wins(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo_root, tmp_path, source, expected
):
    planted = tmp_path / f"order_{expected}.metta"
    planted.write_text(source)
    assert _run_metta(repo_root, planted)[-1] == expected


def test_the_confluence_reporter_analyzes_prelude_registered_rules(repo_root):
    """Every REGISTERED rule enters the analyzed set.

    The prelude's rules never become space atoms (the loader compiles them
    into &self's module), so before the engine's prelude_equation/2 register
    existed the report listed ten registered names and analyzed two rules.
    The closure's symbol count equalling the registered count is the
    invariant; the shipped-tier block shows the ladder pairs are actually
    read, without pinning how many rungs the prelude ships.
    """
    report = _confluence_report(repo_root, [])
    registered = re.search(r"registered translator rules: (\d+),", report)
    analyzed = re.search(
        r"compile-time rule set: \d+ rules over (\d+) defined symbols", report
    )
    assert registered and analyzed, report
    assert int(analyzed.group(1)) == int(registered.group(1))
    assert int(registered.group(1)) > 2
    assert "shipped tier:" in report
    assert "specialization pairs" in report
    assert "EQUIVALENCE OBLIGATION" in report


def test_an_answerless_translator_rule_body_behaves_as_ruled(repo_root, tmp_path):
    """A rule's body is its condition, and the machinery says so.

    Measured 2026-08-19 and left unsettled: a rule whose body had no answer was
    skipped and the next clause tried, which is conditional-rule dispatch
    arriving by accident. Settled 2026-08-21 in favour of that behaviour,
    because it is what every system this rule set is modelled on does: the
    arbiter's own oriented conditional rewriting fires a rule when its left
    side matches and each condition holds (LeaTTa
    MeTTaILProofs/ConditionalCP.lean), CHR tries the next rule when a guard
    fails, Haskell continues with the next alternative when every guard of one
    fails, and Rw-Prolog writes a rule as ``Pattern := Template :- Conditions``.
    """
    fell_through = tmp_path / "fell_through.metta"
    fell_through.write_text(ANSWERLESS_BODY_FALLS_THROUGH)
    assert _run_metta(repo_root, fell_through)[-1] == "two"

    declined = tmp_path / "declined.metta"
    declined.write_text(ANSWERLESS_BODY_ALONE_DECLINES)
    assert _run_metta(repo_root, declined)[-1] == "()"

    # The same equations without the registration, so what the rule adds is
    # the compile time and the commitment to one clause, not the answers.
    as_a_function = tmp_path / "as_a_function.metta"
    as_a_function.write_text(ANSWERLESS_BODY_AS_A_FUNCTION)
    assert _run_metta(repo_root, as_a_function)[-1] == "(two)"

    # And the ruling is written where the confluence verdict is given, because
    # it is what that verdict is worth: a decision about the unconditional
    # system extracted from the heads, a proof obligation about the rules that
    # actually run.
    report = _confluence_report(repo_root, [])
    assert "every translator rule is a CONDITIONAL rewrite rule" in report
    assert "a rule's BODY is its condition" in report
    assert "PROOF OBLIGATION" in report


# The files that make a claim about the compile-time rule set's metatheory:
# the two machinery files, and every file that loads one of them. Each is
# mapped to the relation its own results are about. `check.sh` loads both to
# check for undefined predicates and is not here, because a runner makes no
# claim; it is also not one of the extensions the discovery below walks.
COVERAGE = {
    "engine/trs.pl": {"REWRITING"},
    "engine/narrowing.pl": {"NARROWING"},
    # A THIRD sense of the word, named so it is not read as the second:
    # constructive negation narrows a variable's domain, which is not the
    # relation the termination analysis decides.
    "engine/duals.pl": {"NARROWING"},
    # The registry declares to both analyses: a rule's direction, cost and
    # derived inverse are rewriting, and `extra-variables-exempt` is written
    # for the narrowing termination analysis alone.
    "engine/translator_rules.pl": {"REWRITING", "NARROWING"},
    "tests/prolog/suites/translator/trs.plt": {"REWRITING"},
    "tests/prolog/suites/translator/narrowing.plt": {"NARROWING"},
    "tests/prolog/translator_confluence.pl": {"REWRITING", "NARROWING"},
    "tests/prolog/README.md": {"REWRITING", "NARROWING"},
    "tests/conformance/critical_pairs_run.pl": {"REWRITING"},
    "extensions/python/tests/conformance/test_critical_pair_oracle.py": {"REWRITING"},
    "extensions/python/tests/conformance/test_metatheory.py": {"REWRITING", "NARROWING"},
}

_MACHINERY = ("engine/trs.pl", "engine/narrowing.pl")
_COVERS = re.compile(r"WHAT (?:IT|EACH HALF) COVERS: ([^.]*)")


def _claim_named_by(text):
    """Which of the two relations a file says its own results are about."""
    return {
        term
        for sentence in _COVERS.findall(text)
        for term in ("REWRITING", "NARROWING")
        if term in sentence
    }


def test_each_narrowing_citation_in_the_plan_states_which_it_covers(repo_root):
    """A file borrowing a metatheory result says which relation it covers.

    Narrowing and rewriting are different relations, and a claim about one is
    not a claim about the other.
    Measured 2026-08-18: with `(= (f a) 1)` and `(= (f b) 2)`,
    `!(let $r (f $x) ($x $r))` answers `[(a 1), (b 2)]`, so evaluating
    `(f $x)` INSTANTIATES `$x`. The head is not an instance of the goal, they
    unify, and that is narrowing. Every confluence result this repository
    borrows, Knuth and Bendix through the critical-pair enumerators, is a
    REWRITING result, and Nishida and Vidal's paper exists because termination
    of narrowing does not follow from termination of rewriting.

    The in-repo surface is thinner than the plan that records the same
    correction: the repository cites only what it BUILT ON, which is the
    eleven files COVERAGE names. So this pins those, on both sides. Every one of them says which
    relation its results are about, and the set cannot grow silently, because
    a file that loads engine/trs.pl or engine/narrowing.pl and says nothing
    fails the discovery half below.
    """
    walked = [
        path
        for pattern in ("engine/*.pl", "tests/**/*.pl", "tests/**/*.plt",
                        "tests/**/*.md", "extensions/python/tests/*/test_*.py")
        for path in repo_root.glob(pattern)
    ]
    assert len(walked) > 100, len(walked)

    naming = {
        path.relative_to(repo_root).as_posix()
        for path in walked
        if any(machinery in path.read_text(encoding="utf-8") for machinery in _MACHINERY)
    }
    assert naming == set(COVERAGE), (
        "a file that names the rewriting machinery must say what its results "
        f"cover; unmapped {sorted(naming - set(COVERAGE))}, "
        f"stale {sorted(set(COVERAGE) - naming)}"
    )

    for relative, expected in COVERAGE.items():
        claimed = _claim_named_by((repo_root / relative).read_text(encoding="utf-8"))
        assert claimed == expected, (relative, claimed, expected)

    # The claims are not decoration: the two machinery headers state the
    # relation between the relations, which is the whole content of the
    # correction, and each states it from its own side.
    rewriting = (repo_root / "engine" / "trs.pl").read_text(encoding="utf-8")
    narrowing = (repo_root / "engine" / "narrowing.pl").read_text(encoding="utf-8")
    assert "termination of rewriting\n%   does not imply it" in narrowing
    assert "The reduction to REWRITING is the whole content" in narrowing
    assert "engine/narrowing.pl is the file that" in rewriting
    assert "INSTANTIATES $x" in rewriting
