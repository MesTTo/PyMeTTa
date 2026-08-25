"""Purpose: make every ruled gallery program an explicit blocking corpus.

Guarantees:
  - the gallery is exactly six runnable programs with 45 source-span claims;
    every program verifies one emitted doctest bilingually and prints its own
    checked OK receipt [tested: test_every_gallery_program_runs;
    commit=WORKTREE]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from executable_docs import source_expectations  # noqa: E402  -- tools are executable modules

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
GALLERY = EXAMPLES / "gallery"
PROGRAMS = (
    "ecosystem_graph.py",
    "family_algebras.py",
    "git_like_worlds.py",
    "journaled_observed_store.py",
    "linda_coordination.py",
    "symbolic_tensors.py",
)
CLAIM_COUNTS = {
    "ecosystem_graph.py": 4,
    "family_algebras.py": 20,
    "git_like_worlds.py": 9,
    "journaled_observed_store.py": 5,
    "linda_coordination.py": 6,
    "symbolic_tensors.py": 1,
}


def test_every_gallery_program_runs():
    """Discovery, source law, bilingual examples, and execution gate as one."""
    discovered = tuple(path.name for path in sorted(GALLERY.glob("*.py")))
    assert discovered == PROGRAMS
    assert tuple(CLAIM_COUNTS) == PROGRAMS
    assert sum(CLAIM_COUNTS.values()) == 45
    environment = {
        **os.environ,
        "PYTHONPATH": str(EXAMPLES) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    for name in PROGRAMS:
        program = GALLERY / name
        expectations = source_expectations(program)
        assert len(expectations) == CLAIM_COUNTS[name]
        completed = subprocess.run(
            [sys.executable, str(program)],
            cwd=program.parent,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, f"{name} failed:\n{completed.stdout}\n{completed.stderr}"
        assert "1 bilingual example(s)" in completed.stdout, completed.stdout
        assert f"OK {program.stem}" in completed.stdout, completed.stdout
