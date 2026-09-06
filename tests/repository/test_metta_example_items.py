"""Purpose: the `.metta` examples this library contributed are pytest items,
one per line of repository/metta_examples.txt, each running `sh run.sh` and
reading that run's check marks. Before the collector they were a hardcoded
FILES list parametrised into one test, so `-k`, `--deselect` and a junit report
saw one node where the corpus has eight.
Assumes:
    - the repository root is four directories above this file, the same way
      test_examples_attribution.py derives it
Guarantees:
    - the collector yields exactly the manifest's rows, named for the example
      [tested: test_the_manifest_collects_one_item_per_row; commit=59c3cbf1bc269dfa7194f78da34497f1757a9604]
    - an item runs the example rather than merely naming it
      [tested: test_a_listed_example_runs_as_its_own_item; commit=59c3cbf1bc269dfa7194f78da34497f1757a9604]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PYTHON_ROOT = REPO / "extensions" / "python"
MANIFEST = Path("tests") / "repository" / "metta_examples.txt"


def _rows() -> list[str]:
    return [
        line.split()[0]
        for line in (PYTHON_ROOT / MANIFEST).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _pytest(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run pytest over this seat, from this seat, with its own configuration."""
    return subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            "--rootdir=.", "-c", "pyproject.toml",
            "-p", "no:benchmark", "-p", "no:randomly", "-p", "no:cacheprovider",
            *arguments,
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(PYTHON_ROOT),
        check=False,
    )


def test_the_manifest_collects_one_item_per_row():
    """Each listed example is its own node, named for the example."""
    listed = _rows()
    assert listed, f"{MANIFEST} lists no examples"
    result = _pytest("--collect-only", str(MANIFEST))
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    collected = [
        line.split("::", 1)[1]
        for line in result.stdout.splitlines()
        if line.startswith(f"{MANIFEST.as_posix()}::")
    ]
    assert collected == listed, (
        f"the collector yielded {collected}, and {MANIFEST} lists {listed}"
    )


def test_a_listed_example_runs_as_its_own_item():
    """One node runs its example through run.sh and reads the check marks.

    The smallest listed example, because this proves the item RUNS rather than
    that a particular program is correct; that is the example's own job and the
    corpus runner's.
    """
    smallest = min(_rows(), key=lambda name: (REPO / name).stat().st_size)
    result = _pytest(f"{MANIFEST.as_posix()}::{smallest}")
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert "1 passed" in result.stdout, result.stdout[-2000:]
