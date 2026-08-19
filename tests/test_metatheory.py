"""Purpose: the three acceptance criteria of the metatheory cluster, each
    checked against behaviour rather than against prose. The confluence checker
    is an ADAPTATION whose provenance and whose termination caveat are both
    recorded and both true; the compile-time rule set's termination is
    ESTABLISHED or the failure is NAMED, with no third answer; and two
    translator rules that overlap are REPORTED with the overlap named rather
    than silently ordered.
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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Every reason src/narrowing.pl can give for not establishing termination. A
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

OVERLAPPING_RULES = """(= (m2 a) (quote one))
(= (m2 $x) (quote two))
!(add-translator-rule! m2)
(= (usem2) (m2 a))
!(usem2)
"""

REVERSED_RULES = """(= (m2 $x) (quote two))
(= (m2 a) (quote one))
!(add-translator-rule! m2)
(= (usem2) (m2 a))
!(usem2)
"""

CLEAN_RULES = """(= (m5 $x) (quote (cons 5 $x)))
!(add-translator-rule! m5)
(= (usem5) (m5 (6)))
!(usem5)
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


def test_the_confluence_checker_records_its_provenance_and_its_termination_caveat(
    repo_root,
):
    checker = _unwrapped(repo_root / "src" / "trs.pl")

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
            "use_module('../../src/trs.pl'), "
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
    lib/lib_builtin_types.metta declares the builtin's type and registers
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


def test_the_compile_time_rule_set_is_shown_terminating_or_the_failure_is_named(
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


def test_the_established_route_names_what_decided_it(repo_root, tmp_path):
    planted = tmp_path / "clean.metta"
    planted.write_text(CLEAN_RULES)
    report = _confluence_report(repo_root, [planted])
    assert _termination_line(report).startswith("termination: ESTABLISHED.")
    assert "argument filtering transformation" in report
    assert "recursive path order" in report
    assert "filtering: " in report
    assert "precedence, lowest first: " in report


def test_overlapping_translator_rules_are_reported_with_the_overlap_named(
    repo_root, tmp_path
):
    planted = tmp_path / "overlap.metta"
    planted.write_text(OVERLAPPING_RULES)
    report = _confluence_report(repo_root, [planted])

    # Named: which two rules, where they overlap, and what each of them gives.
    assert "OVERLAP counterexample: rule 1 (m2 a) and rule 2 (m2 $" in report
    assert "at position []" in report
    assert "rule 1 gives (quote one)" in report
    assert "rule 2 gives (quote two)" in report
    assert "conclusion: NOT LOCALLY CONFLUENT." in report

    # The decidable fragment, and which side of it this rule set is on.
    assert "Knuth and Bendix (1970)" in report
    assert "UNCONDITIONAL" in report
    assert "CONDITIONAL rule" in report
    assert "undecidable in general" in report

    # And the thing the report warns about is real: the same two rules in the
    # other order make the engine answer differently.
    reversed_file = tmp_path / "reversed.metta"
    reversed_file.write_text(REVERSED_RULES)
    assert _run_metta(repo_root, planted)[-1] == "one"
    assert _run_metta(repo_root, reversed_file)[-1] == "two"


def test_a_rule_set_without_an_overlap_is_reported_as_having_none(
    repo_root, tmp_path
):
    planted = tmp_path / "clean.metta"
    planted.write_text(CLEAN_RULES)
    report = _confluence_report(repo_root, [planted])
    assert "OVERLAP" not in report
    assert "0 divergent" in report
    assert "conclusion: CONFLUENT." in report


def test_the_detector_is_run_against_its_own_planted_rule_sets(repo_root):
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
def test_assertion_order_alone_decides_which_overlapping_rule_wins(
    repo_root, tmp_path, source, expected
):
    planted = tmp_path / f"order_{expected}.metta"
    planted.write_text(source)
    assert _run_metta(repo_root, planted)[-1] == expected
