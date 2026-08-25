"""Purpose: make every ruled gallery program an explicit blocking corpus.

Guarantees:
  - the gallery is exactly six programs carrying 45 source-span claims
    [tested: test_the_gallery_is_exactly_the_six_ruled_programs;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - every program verifies one emitted doctest bilingually and prints its own
    checked OK receipt; the two that reach an ecosystem package skip where
    that package is absent rather than making it a dependency of the library
    [tested: test_a_gallery_program_runs; commit=WORKTREE]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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
#: The two programs whose subject IS an ecosystem package. Neither is a
#: dependency of the library, and the minimal version matrix installs neither,
#: so each skips there exactly as test_arrays.py skips without numpy. The
#: other four run everywhere, and the gate environment installs both extras,
#: so all six are blocking on every push.
REQUIREMENTS = {
    "ecosystem_graph.py": "networkx",
    "symbolic_tensors.py": "numpy",
}


def test_the_gallery_is_exactly_the_six_ruled_programs():
    """Discovery and the source-claim law, independent of any package."""
    discovered = tuple(path.name for path in sorted(GALLERY.glob("*.py")))
    assert discovered == PROGRAMS
    assert tuple(CLAIM_COUNTS) == PROGRAMS
    assert sum(CLAIM_COUNTS.values()) == 45
    assert set(REQUIREMENTS) <= set(PROGRAMS)
    for name in PROGRAMS:
        assert len(source_expectations(GALLERY / name)) == CLAIM_COUNTS[name]


@pytest.mark.parametrize("name", PROGRAMS)
def test_a_gallery_program_runs(name):
    """Execution, the bilingual example, and the program's own OK receipt."""
    requirement = REQUIREMENTS.get(name)
    if requirement is not None:
        pytest.importorskip(requirement)
    program = GALLERY / name
    environment = {
        **os.environ,
        "PYTHONPATH": str(EXAMPLES) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
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
