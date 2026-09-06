"""Purpose: a finding's remedy, applied.

The same repair reaches a space through apply(), a file through fix_file(),
and an editor through the LSP diagnostics `python -m metta lint --json`
prints.

Guarantees:
  - a duplicate equation and a constant `if` round-trip through --fix: the
    file relints clean, the author's variable names survive, and the
    remaining findings decide the exit code [tested:
    test_fix_removes_a_duplicate_equation_and_relints_clean,
    test_the_cli_fixes_a_file_and_reports_what_it_left; commit=WORKTREE]
  - --json prints one LSP Diagnostic per line, zero-based, with the remedy
    under data [tested: test_lint_json_prints_one_lsp_diagnostic_per_line;
    commit=WORKTREE]
  - a file that changed since lint read it is refused whole, with nothing
    written [tested: test_fix_refuses_a_file_that_changed_since_lint_read_it;
    commit=WORKTREE]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from metta.lint import apply, diagnostics, fix_file, lint, lint_file

_DUPLICATE = "(= (fx-twin $x) $x)\n(= (fx-twin $y) $y)\n"
_SIMPLIFIABLE = "(= (fx-plain $value) (if True $value 0))\n"


@pytest.fixture()
def m(metta):
    """One scratch space per test, dropped when the test ends."""
    with metta._new_space() as space:
        yield space


def _metta(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the packaged CLI as a real process, the way a user does."""
    return subprocess.run(
        [sys.executable, "-m", "metta", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_finding_renders_its_remedy_in_place_of_the_atom(m):
    """One line, and the remedy's title is what it says."""
    m.run(_SIMPLIFIABLE)
    finding = next(f for f in lint(m) if f.kind == "constant-if-true")
    assert finding.remedy is not None
    assert finding.remedy.applicability == "machine"
    assert str(finding) == f"[constant-if-true] {finding.message}"
    assert finding.message.endswith(f"(fix: {finding.remedy.title})")
    assert str(finding.autofix) == str(finding.remedy.replace[1])


def test_a_duplicate_equation_carries_a_removal_remedy(m):
    """A multiset holding one equation twice repairs by dropping one copy."""
    m.run(_DUPLICATE)
    finding = next(f for f in lint(m) if f.kind == "duplicate-equation")
    assert finding.autofix is None
    assert finding.remedy is not None
    assert finding.remedy.replace == (finding.atom, None)
    assert finding.remedy.applicability == "machine"


def test_apply_repairs_a_space_and_names_what_it_left(m):
    """The space face of the repair: remove and add, nothing else."""
    m.run(_DUPLICATE + _SIMPLIFIABLE + "(: fx-ghost (-> Number Number))\n")
    repair = apply(m)
    assert {finding.kind for finding in repair.applied} == {
        "duplicate-equation",
        "constant-if-true",
    }
    assert [skipped.finding.kind for skipped in repair.skipped] == [
        "declared-but-undefined"
    ]
    assert repair.skipped[0].reason == "the finding carries no remedy"
    assert repair.remaining == 1
    assert [f.kind for f in lint(m)] == ["declared-but-undefined"]


def test_apply_leaves_a_maybe_remedy_alone(m):
    """Rustc's rule: only MachineApplicable is written without being asked."""
    m.run("(= (fx-caller) (car-atomm 1))")
    finding = next(f for f in lint(m) if f.kind == "possibly-undefined-reference")
    assert finding.remedy is not None
    assert finding.remedy.applicability == "maybe"
    repair = apply(m, [finding])
    assert repair.applied == ()
    assert repair.skipped[0].reason == "the remedy is maybe, not machine"


def test_fix_removes_a_duplicate_equation_and_relints_clean(tmp_path, metta):
    """The whole round trip, ending where lint has nothing left to say."""
    target = tmp_path / "twins.metta"
    target.write_text(_DUPLICATE + _SIMPLIFIABLE, encoding="utf-8")
    repair = fix_file(target, m=metta)
    assert repair.written is True
    assert repair.refused is None
    assert {finding.kind for finding in repair.applied} == {
        "duplicate-equation",
        "constant-if-true",
    }
    assert repair.remaining == 0
    assert target.read_text(encoding="utf-8") == (
        "(= (fx-twin $y) $y)\n(= (fx-plain $value) $value)\n"
    )
    assert lint_file(target, m=metta) == []


def test_a_fix_keeps_the_names_the_author_wrote(tmp_path, metta):
    """A machine rewrite may not rename the variables in someone's file."""
    target = tmp_path / "named.metta"
    target.write_text("(= (fx-named $original) (if True $original 0))\n", encoding="utf-8")
    fix_file(target, m=metta)
    assert target.read_text(encoding="utf-8") == "(= (fx-named $original) $original)\n"


def test_fix_refuses_a_file_that_changed_since_lint_read_it(tmp_path, metta):
    """The digest is this library's document version, and it is checked."""
    target = tmp_path / "moving.metta"
    target.write_text(_DUPLICATE, encoding="utf-8")
    held = lint_file(target, m=metta)
    target.write_text(_DUPLICATE + "(fx-note added)\n", encoding="utf-8")
    repair = fix_file(target, held, m=metta)
    assert repair.written is False
    assert repair.refused == "the file changed since lint read it"
    assert repair.remaining == len(held)
    assert target.read_text(encoding="utf-8").endswith("(fx-note added)\n")


def test_an_unanchored_finding_is_listed_rather_than_guessed(tmp_path, metta):
    """A finding no single form wrote has no line, so it is never written."""
    target = tmp_path / "unanchored.metta"
    target.write_text("(: fx-ghost (-> Number Number))\n", encoding="utf-8")
    repair = fix_file(target, m=metta)
    assert repair.written is False
    assert [skipped.reason for skipped in repair.skipped] == [
        "the finding carries no remedy"
    ]


def test_lint_json_prints_one_lsp_diagnostic_per_line(tmp_path):
    """LSP 3.17's own object, zero-based, with the remedy preserved in data."""
    target = tmp_path / "diagnosed.metta"
    target.write_text(_SIMPLIFIABLE, encoding="utf-8")
    finished = _metta("lint", "--json", str(target))
    assert finished.returncode == 1, finished.stderr
    lines = [json.loads(line) for line in finished.stdout.splitlines()]
    assert len(lines) == 1
    diagnostic = lines[0]
    assert diagnostic["code"] == "constant-if-true"
    assert diagnostic["source"] == "metta"
    assert diagnostic["severity"] == 3
    assert diagnostic["range"]["start"] == {"line": 0, "character": 0}
    assert diagnostic["range"]["end"]["character"] == len(_SIMPLIFIABLE.rstrip("\n"))
    remedy = diagnostic["data"]["remedy"]
    assert remedy["applicability"] == "machine"
    assert remedy["kind"] == "quickfix"
    stored, replacement = remedy["replace"]
    #: The stored atom carries the ENGINE's variable name, which is why the
    #: file rewrite renames it back; here the shape is what matters.
    variable = re.fullmatch(r"\(= \(fx-plain (\$\S+)\) \(if True \1 0\)\)", stored)
    assert variable is not None, stored
    assert replacement == f"(= (fx-plain {variable[1]}) {variable[1]})"
    assert diagnostic["data"]["docs"].startswith("https://")


def test_a_removal_remedy_reaches_json_as_remove(tmp_path, metta):
    """The JSON act vocabulary is the atom's: a removal is `remove`."""
    target = tmp_path / "removed.metta"
    target.write_text(_DUPLICATE, encoding="utf-8")
    diagnostic = diagnostics(lint_file(target, m=metta))[0]
    assert "remove" in diagnostic["data"]["remedy"]
    assert "replace" not in diagnostic["data"]["remedy"]


def test_the_cli_fixes_a_file_and_reports_what_it_left(tmp_path):
    """`lint --fix` exits on what remains, not on what it repaired."""
    target = tmp_path / "cli.metta"
    target.write_text(_DUPLICATE + "(: fx-ghost (-> Number Number))\n", encoding="utf-8")
    fixed = _metta("lint", "--fix", str(target))
    assert fixed.returncode == 1, fixed.stderr
    assert "fixed: [duplicate-equation]" in fixed.stdout
    assert "not applied: the finding carries no remedy" in fixed.stdout
    clean = tmp_path / "clean.metta"
    clean.write_text(_DUPLICATE, encoding="utf-8")
    repaired = _metta("lint", "--fix", str(clean))
    assert repaired.returncode == 0, repaired.stderr
    assert "no findings remain" in repaired.stdout


def test_json_and_fix_are_one_or_the_other(tmp_path):
    """Two ways to answer one lint is a coin toss, so argparse refuses it."""
    target = tmp_path / "both.metta"
    target.write_text(_DUPLICATE, encoding="utf-8")
    refused = _metta("lint", "--json", "--fix", str(target))
    assert refused.returncode == 2
    assert "not allowed with argument" in refused.stderr
