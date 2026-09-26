"""Purpose: hold the pytest lane's runner to leaving no cache in the seat.

test.sh passes `-p no:cacheprovider` and says why beside it: the directory a
run would leave .pytest_cache in is the one the instructions lane measures
from. This file runs test.sh on a planted test, rooted in a scratch directory
so that the cache a run writes lands there, and looks at what the run left.
Assumes: this seat's test.sh and pyproject.toml, and the interpreter running
  the suite.
Guarantees:
  - a run through test.sh writes no .pytest_cache, and one given
    `-p cacheprovider` writes it, so the runner's default decides and a
    caller's own flag still wins
    [tested 2026-09-26T10:26:02+10:00: test_the_pytest_lane_writes_no_cache_unless_asked]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys

import pytest

from metta._roots import workspace

SEAT = workspace() / "extensions" / "python"

#: Collects and passes with nothing but pytest itself.
PLANTED = "def test_planted():\n    pass\n"


@pytest.mark.parametrize(
    ("flags", "cached"),
    [((), False), (("-p", "cacheprovider"), True)],
    ids=["runner-default", "caller-flag"],
)
def test_the_pytest_lane_writes_no_cache_unless_asked(tmp_path, flags, cached):
    """What test.sh writes, read from a run rooted in tmp_path.

    The cache directory resolves against the rootdir, so the run writes there
    and never into the seat.
    """
    planted = tmp_path / "test_planted.py"
    planted.write_text(PLANTED, encoding="utf-8")
    result = subprocess.run(
        [
            "sh", str(SEAT / "test.sh"), "-n", "0",
            f"--rootdir={tmp_path}", "-c", str(SEAT / "pyproject.toml"),
            *flags, str(planted),
        ],
        env={**os.environ, "CHECK_PY": sys.executable},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    left = sorted(entry.name for entry in tmp_path.iterdir())
    assert ((tmp_path / ".pytest_cache").is_dir(), left) == (cached, left)
