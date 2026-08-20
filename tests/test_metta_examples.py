"""Purpose: the engine's own .metta example files as pytest items, so the
python suite runs the MeTTa-language tests the same way test.sh does: every
!(test ...) in the file must print its check mark and none may print a
cross. Covers the files this library added; the engine's full sweep stays
test.sh's job.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# The .metta test files this library contributed.
FILES = [
    "measure.metta",
    "soft.metta",
    "python_booleans.metta",
    "math_exp_random.metta",
    "if_branch_binding.metta",
]


@pytest.mark.parametrize("name", FILES)
def test_metta_file(name):
    result = subprocess.run(
        ["sh", "run.sh", f"examples/{name}"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr[:800]
    verdicts = [
        line for line in result.stdout.splitlines() if " should " in line
    ]
    assert verdicts, f"{name} asserted nothing"
    crosses = [line for line in verdicts if "❌" in line]
    assert not crosses, "\n".join(crosses)
    assert all("✅" in line for line in verdicts)
