"""Purpose: every example in the topical folder tree runs and verifies
itself, or skips for a named missing dependency; an example that stops
working fails the build, so the tree cannot drift from the library.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_ROOT = Path(__file__).resolve().parents[1] / "examples"
EXAMPLES = sorted(
    path for path in EXAMPLES_ROOT.rglob("*.py") if path.name != "_common.py"
)


def _example_id(path: Path) -> str:
    return path.relative_to(EXAMPLES_ROOT).with_suffix("").as_posix()


@pytest.mark.parametrize("example", EXAMPLES, ids=_example_id)
def test_example_runs_and_verifies_itself(example):
    repo = EXAMPLES_ROOT.parents[1]
    result = subprocess.run(
        [sys.executable, str(example)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(example.parent),
        env={
            **os.environ,
            "PETTA_PATH": str(repo),
            "JAX_PLATFORMS": "cpu",
            "PYTHONPATH": str(EXAMPLES_ROOT)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
        },
    )
    output = result.stdout
    if result.returncode == 0 and output.startswith("SKIP:"):
        pytest.skip(output.strip())
    assert result.returncode == 0, (
        f"{_example_id(example)} failed:\n{result.stdout}\n{result.stderr[-2000:]}"
    )
    assert f"OK {example.stem}" in output, (
        f"{_example_id(example)} did not verify itself:\n{output}"
    )
