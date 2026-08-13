"""Purpose: every example runs and verifies itself, or skips for a named
missing dependency; an example that stops working fails the build, so the
folder cannot drift from the library.
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

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("[0-9]*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_example_runs_and_verifies_itself(example):
    repo = example.resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(example)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(example.parent),
        env={**os.environ, "PETTA_PATH": str(repo), "JAX_PLATFORMS": "cpu"},
    )
    output = result.stdout
    if result.returncode == 0 and output.startswith("SKIP:"):
        pytest.skip(output.strip())
    assert result.returncode == 0, f"{example.name} failed:\n{result.stdout}\n{result.stderr[-2000:]}"
    assert f"OK {example.stem}" in output, f"{example.name} did not verify itself:\n{output}"
