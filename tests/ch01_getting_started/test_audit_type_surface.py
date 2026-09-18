"""Purpose: run the owned typing consumer and its required rejection controls.

`tests/typing/audit_surface.py` asserts the concrete types a downstream checker
sees at the registry, result, remote and table doors, and its `type: ignore`
lines are negative controls under `warn_unused_ignores`: the day a wrong
assignment or a misspelled export stops being refused, the fixture fails.
The gate's mypy lane reads `files = ["metta"]` and never opens the suite, so
the consumer runs here, the way the root and configuration consumers run in
tests/repository/test_artifact_projections.py.
Guarantees:
  - the consumer passes mypy with every negative control still refused
    [tested: test_audit_owned_type_surface]
"""

import subprocess
import sys
from pathlib import Path

SEAT = Path(__file__).resolve().parents[2]


def test_audit_owned_type_surface(tmp_path):
    """Wrong assignments must fail while accepted field projections stay precise."""
    command = [sys.executable, "-m", "mypy", "--cache-dir", str(tmp_path / "cache"),
               "--follow-imports=silent", "tests/typing/audit_surface.py"]
    result = subprocess.run(command, cwd=SEAT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
