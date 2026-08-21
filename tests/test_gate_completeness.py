"""Purpose: pin Phase 0 outcomes that were reached and then left
unpinned, so each one regresses loudly instead of silently. An outcome
nothing tests is an outcome that comes back: the performance oracles were
deleted rather than gated, `test.sh` computed a verdict summary it did not
print, MeTTa's generated Prolog contains no cut, and Ruff's added families
remain enabled with reviewed line-level suppressions.
Assumes:
    - the repository root is two directories above this file, the same way
      test_example_parity.py derives it
    - `m.disassemble/1` answers the Prolog text a MeTTa equation compiled
      to [source: bindings/python/petta/space.py:MeTTa.disassemble;
      commit=dcfc20be4933c19140ccb5759291401d13058301]
Guarantees:
    - each test fails if its outcome is reverted, which is what makes it
      evidence rather than decoration
      [tested: test_the_ruff_configuration_enables_every_family_or_records_why_not;
      commit=dcfc20be4933c19140ccb5759291401d13058301]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import re
import subprocess
import sys
import tokenize
import tomllib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PYTHON_ROOT = REPO / "bindings" / "python"
RUFF_CONFIGS = (REPO / "pyproject.toml", PYTHON_ROOT / "pyproject.toml")
RUFF_SCOPE = ("petta", "tests", "bench.py")
REQUIRED_RUFF_FAMILIES = frozenset({"FBT", "N", "A", "D", "ARG", "PERF", "C90", "TRY", "EM"})
RUFF_SUPPRESSION_GUARDS = frozenset({"RUF100", "RUF103"})
RUFF_FAMILY_BURN_DOWN = {
    "FBT": 55,
    "N": 35,
    "A": 8,
    # 2112 -> 2114 at the p12-space-model merge: its two new test modules
    # carry the repository's obligation-header docstring convention, whose
    # Purpose/Guarantees block is a deliberate per-line D205 suppression.
    # 2114 -> 2119, and ARG 134 -> 139, C90 16 -> 24, TRY 21 -> 23, at the
    # p5-surface-cluster merge: its twenty-five rows add new modules whose
    # obligation headers carry the D205 convention, signature-reflection
    # test doubles whose parameters must stay visible (ARG), registration
    # and annotation walkers kept whole by design (C901), and two internal
    # invariant raises that deliberately keep their exception class
    # (TRY004). Every one is a per-line suppression with its own reason.
    "D": 2119,
    "ARG": 139,
    "PERF": 0,
    "C90": 24,
    "TRY": 23,
    "EM": 0,
}

FILE_OR_RANGE_SUPPRESSION = re.compile(r"(?i)^#\s*(?:ruff|flake8)\s*:\s*(?:noqa|disable|enable)\b")
LINE_NOQA = re.compile(r"(?i)^#\s*noqa\b")
CANONICAL_NOQA = re.compile(
    r"^#\s*(?i:noqa):\s*"
    r"(?P<codes>[A-Z]+[0-9]{3,4}(?:,\s+[A-Z]+[0-9]{3,4})*)"
    r"\s+--\s+(?P<reason>\S(?:.*\S)?)\s*$"
)
GENERIC_REASON = re.compile(r"(?i)\b(?:legacy|debt|temporary|later|todo|fixme|burn[- ]?down)\b")


def _selector_hits_family(selector: str, family: str) -> bool:
    selector = selector.upper()
    return selector == "ALL" or re.fullmatch(rf"{re.escape(family)}[0-9]*", selector) is not None


def _selector_covers_rule(selector: str, rule: str) -> bool:
    selector = selector.upper()
    return selector == "ALL" or rule.startswith(selector)


def _required_family(code: str) -> str | None:
    for family in sorted(REQUIRED_RUFF_FAMILIES, key=len, reverse=True):
        if re.fullmatch(rf"{re.escape(family)}[0-9]+", code):
            return family
    return None


def _ignore_entries(ruff: dict):
    lint = ruff["lint"]
    for section_name, section in (("[tool.ruff]", ruff), ("[tool.ruff.lint]", lint)):
        for key in ("ignore", "extend-ignore"):
            for selector in section.get(key, ()):
                yield f"{section_name}.{key}", selector
        for key in ("per-file-ignores", "extend-per-file-ignores"):
            for pattern, selectors in section.get(key, {}).items():
                for selector in selectors:
                    yield f"{section_name}.{key}[{pattern!r}]", selector


def _ruff_findings(*extra: str) -> list[dict]:
    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--output-format=json",
        *extra,
        *RUFF_SCOPE,
    ]
    completed = subprocess.run(
        command,
        cwd=PYTHON_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode in {0, 1}, (
        f"{command!r} exited {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        msg = (
            f"{command!r} did not emit Ruff JSON\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
        raise AssertionError(msg) from exc


def _assert_ruff_configuration(path: Path, ruff: dict) -> None:
    lint = ruff["lint"]
    selected = set(lint.get("select", ())) | set(lint.get("extend-select", ()))
    assert REQUIRED_RUFF_FAMILIES <= selected, (
        f"{path}: missing exact family selectors {sorted(REQUIRED_RUFF_FAMILIES - selected)}"
    )
    assert lint["pydocstyle"]["convention"] == "google"
    for guard in RUFF_SUPPRESSION_GUARDS:
        assert any(_selector_covers_rule(selector, guard) for selector in selected), (
            f"{path}: {guard} is not selected"
        )

    hidden = []
    for location, selector in _ignore_entries(ruff):
        required = sorted(
            family for family in REQUIRED_RUFF_FAMILIES if _selector_hits_family(selector, family)
        )
        guards = sorted(
            guard for guard in RUFF_SUPPRESSION_GUARDS if _selector_covers_rule(selector, guard)
        )
        if required or guards:
            hidden.append((location, selector, required, guards))
    assert not hidden, f"{path}: required Ruff rules are ignored: {hidden}"


def _audit_policy_suppressions() -> list[tuple[str, list[str], str]]:
    suppressions = []
    sources = [
        *sorted((PYTHON_ROOT / "petta").rglob("*.py")),
        *sorted((PYTHON_ROOT / "tests").rglob("*.py")),
        PYTHON_ROOT / "bench.py",
    ]
    for path in sources:
        with path.open("rb") as stream:
            comments = (
                token
                for token in tokenize.tokenize(stream.readline)
                if token.type == tokenize.COMMENT
            )
            for token in comments:
                comment = token.string
                location = f"{path.relative_to(REPO)}:{token.start[0]}"
                assert not FILE_OR_RANGE_SUPPRESSION.search(comment), (
                    f"{location}: file-level and range Ruff suppressions are forbidden: {comment}"
                )
                if not LINE_NOQA.search(comment):
                    continue
                assert ":" in comment, f"{location}: blanket noqa is forbidden: {comment}"
                code_text = comment.split(":", 1)[1].split(" -- ", 1)[0]
                candidates = re.findall(r"[A-Za-z]+[0-9]*", code_text)
                touches_policy = any(
                    _required_family(candidate.upper()) is not None
                    or candidate.upper() in RUFF_SUPPRESSION_GUARDS
                    for candidate in candidates
                )
                if not touches_policy:
                    continue
                match = CANONICAL_NOQA.fullmatch(comment)
                assert match is not None, f"{location}: use full codes and ` -- reason`: {comment}"
                codes = [code.strip() for code in match.group("codes").split(",")]
                assert len(codes) == len(set(codes)), (
                    f"{location}: duplicate suppression code: {comment}"
                )
                forbidden_guards = RUFF_SUPPRESSION_GUARDS.intersection(codes)
                assert not forbidden_guards, (
                    f"{location}: cannot suppress {sorted(forbidden_guards)}"
                )
                reason = match.group("reason")
                assert len(reason) >= 20 and GENERIC_REASON.search(reason) is None, (
                    f"{location}: replace the generic suppression reason: {reason!r}"
                )
                suppressions.append((location, codes, reason))
    return suppressions


def test_the_ruff_configuration_enables_every_family_or_records_why_not():
    """Keep every P0.13 family enabled and every suppression narrow and reviewed."""
    configurations = [
        tomllib.loads(path.read_text(encoding="utf-8"))["tool"]["ruff"] for path in RUFF_CONFIGS
    ]
    assert configurations[0] == configurations[1]
    for path, ruff in zip(RUFF_CONFIGS, configurations, strict=True):
        _assert_ruff_configuration(path, ruff)

    suppressions = _audit_policy_suppressions()
    assert suppressions, "the suppression audit saw no P0.13 line-level decisions"

    clean = _ruff_findings()
    assert not clean, f"configured Ruff gate is not clean: {clean[:20]}"

    ignored = _ruff_findings("--ignore-noqa")
    counts = Counter(
        family for finding in ignored if (family := _required_family(finding["code"])) is not None
    )
    regressions = {
        family: (counts[family], limit)
        for family, limit in RUFF_FAMILY_BURN_DOWN.items()
        if counts[family] > limit
    }
    assert not regressions, (
        f"P0.13 suppression burn-down increased (observed, maximum): {regressions}"
    )


def test_no_ungated_prolog_performance_oracle_returns():
    """P0.8 asked that the eight Prolog performance oracles be gated
    against a committed baseline OR deleted, and the delete branch is what
    happened. Nothing stopped them coming back, and an oracle that runs
    against no baseline is a file that passes by existing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    oracles = sorted(p.relative_to(REPO) for p in (REPO / "tests" / "performance").rglob("*.pl"))
    assert not oracles, (
        f"{len(oracles)} Prolog performance oracle(s) are back and nothing "
        f"compares them to a baseline: {[str(p) for p in oracles]}"
    )


def test_the_runner_prints_every_assertion_it_collects():
    """P0.10. `test.sh` collected the `is ... should ...` lines into a
    variable and, at the time of the audit, never printed it. A verdict
    computed and dropped is worse than one never computed, because the run
    looks like it reported.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    text = (REPO / "test.sh").read_text(encoding="utf-8")
    assigned = [n for n, line in enumerate(text.splitlines(), 1) if "assertions=" in line]
    assert assigned, "test.sh no longer collects assertions; this test guards the wrong thing now"
    used = [
        n
        for n, line in enumerate(text.splitlines(), 1)
        if '"$assertions"' in line and "assertions=" not in line
    ]
    assert used, (
        f"test.sh assigns assertions at line(s) {assigned} and never reads it back; "
        "the summary it computes is dropped"
    )


def test_a_generated_clause_carries_no_cut(metta):
    """P0.12. Generated code is worse than hand-written code for a stray
    cut, because nobody reads it: a cut in a compiled equation would make
    the second clause unreachable and the program would simply answer less.

    Two clauses for one name is the shape that shows it. `(f 0)` answers
    both `zero` and `other` only if neither clause cut, so this asserts the
    behaviour AND the text, and the behaviour is the part that matters.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("(= (petta-cut-probe 0) zero)")
    metta.run("(= (petta-cut-probe $x) other)")
    compiled = metta.disassemble("petta-cut-probe")
    assert "!" not in compiled, f"a generated clause contains a cut:\n{compiled}"
    answers = [str(a) for group in metta.run("!(petta-cut-probe 0)") for a in group]
    assert answers == ["zero", "other"], (
        f"both clauses should answer; got {answers}, which is what a cut looks like"
    )
