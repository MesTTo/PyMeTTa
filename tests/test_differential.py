"""Purpose: the differential oracle. Each example program runs twice, through
the CLI exactly as run.sh invokes it and through the library's structured
load in a fresh subprocess, and the outputs must agree byte for byte. The
library side re-renders every answer through the engine's own printer after a
full wire round trip, so agreement proves the structured path preserves what
the CLI computes, per real program rather than per hand-picked case.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import alpha

REPO = Path(__file__).resolve().parents[3]

#: The canonical text form lives in one place, because two lanes need it and a
#: third spelling of the law's own relation would be a third thing to drift.
_normalize = alpha.canonical

# Fast, deterministic examples covering the semantic surface: arithmetic,
# matching, nondeterminism, control, types, states, strings, lambdas,
# recursion, and the Python bridge. Slow or environment-dependent examples
# (network, chess search, MORK) stay out, as test.sh itself leaves some out.
EXAMPLES = [
    "factorial.metta",
    "fib.metta",
    "and_or.metta",
    "case.metta",
    "let_superpose_if_case.metta",
    "collapse.metta",
    "string.metta",
    "types.metta",
    "state.metta",
    "lambda.metta",
    "peano.metta",
    "listhead.metta",
    "math.metta",
    "matchsingle.metta",
    "superpose_nested.metta",
    "python.metta",
    "python_import.metta",
]

_LIBRARY_RUNNER = r"""
import os, sys
sys.path.insert(0, {python_dir!r})
os.environ["PETTA_PATH"] = {repo!r}
from petta import MeTTa

m = MeTTa().self
groups = m.load(sys.argv[1])
rt = m.runtime
for group in groups:
    for atom in group:
        row = rt.once("petta_py_swrite(W, S)", W=atom.to_wire())
        print(row["S"])
"""


def _cli_output(example: Path) -> str:
    result = subprocess.run(
        ["swipl", "--stack_limit=8g", "-q", "-s", str(REPO / "engine" / "main.pl"),
         "--", str(example), "silent"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
    )
    assert result.returncode == 0, f"CLI failed on {example.name}: {result.stderr[:500]}"
    return result.stdout


def _library_output(example: Path) -> str:
    script = _LIBRARY_RUNNER.format(python_dir=str(REPO / "bindings" / "python"), repo=str(REPO))
    result = subprocess.run(
        [sys.executable, "-c", script, str(example)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO / "bindings" / "python")},
    )
    assert result.returncode == 0, f"library failed on {example.name}: {result.stderr[:500]}"
    return result.stdout


@pytest.mark.parametrize("name", EXAMPLES)
def test_library_agrees_with_cli(name):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    example = REPO / "examples" / name
    assert example.exists(), f"missing example {name}"
    assert _normalize(_library_output(example)) == _normalize(_cli_output(example))
