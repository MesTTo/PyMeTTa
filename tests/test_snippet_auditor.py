"""Purpose: prove check.sh runs the real website snippet auditor as REPORT.
Guarantees:
  - the auditor's fixed-baseline output reaches the gate log
    [tested: test_the_snippet_auditor_runs_from_the_gate; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "website" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_snippets as auditor  # noqa: E402


def test_the_snippet_auditor_runs_from_the_gate(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    gate = (repo_root / "check.sh").read_text(encoding="utf8")
    assert (
        'run REPORT snippets    "$PY" "$HERE/website/scripts/audit_snippets.py"'
        in gate
    )

    # The child's tiering is this test's to choose, not the caller's: a
    # full battery run under GATE_ONLY=1 leaked that variable in here,
    # the child skipped every REPORT lane including the one under test,
    # and the assertion read an empty summary [measured 2026-08-21].
    child_env = {k: v for k, v in os.environ.items() if k != "GATE_ONLY"}
    child_env["CHECK_PY"] = sys.executable
    run = subprocess.run(
        ["sh", "check.sh", "snippets"],
        cwd=repo_root,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    log = run.stdout + run.stderr
    assert run.returncode == 0, log
    assert "=== snippets [REPORT] ===" in log
    assert "snippet provenance backlog: 66 of 72 remain" in log
    assert "tracked in website/scripts/snippet_backlog.tsv" in log
    assert "guide/atoms-terms.md fence 2:" in log
    assert "REPORT snippets     findings" in log


def test_the_snippet_backlog_cannot_grow(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    enlarged = tmp_path / "snippet_backlog.tsv"
    enlarged.write_text(
        auditor.BACKLOG.read_text(encoding="utf8")
        + f"OPEN\tnew-page.md\t1\t{'0' * 64}\tnew finding\n",
        encoding="utf8",
    )
    monkeypatch.setattr(auditor, "BACKLOG", enlarged)
    with pytest.raises(SystemExit, match="expected the fixed 72-entry baseline, found 73"):
        auditor._backlog()


def test_a_missing_snippet_backlog_is_named(monkeypatch, repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    missing = repo_root / "website" / "scripts" / "missing-snippet-backlog.tsv"
    monkeypatch.setattr(auditor, "BACKLOG", missing)
    with pytest.raises(SystemExit, match="snippet backlog missing: website/scripts/"):
        auditor._backlog()
