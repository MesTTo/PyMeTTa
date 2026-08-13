"""Purpose: the two lines every example needs: make petta importable from a
repo checkout and point PETTA_PATH at it, then a tiny check helper that
makes each example self-verifying rather than a printout to trust.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "python"))
os.environ.setdefault("PETTA_PATH", str(REPO))


def check(label, got, expected=None):
    """Print one result and assert it: an example is a claim, so it verifies
    itself the way a test would, and a wrong output fails loudly."""
    if expected is not None:
        assert got == expected, f"{label}: expected {expected!r}, got {got!r}"
    else:
        assert got, f"{label}: expected a truthy result, got {got!r}"
    print(f"  {label}: {got}")


def skip(reason):
    print(f"SKIP: {reason}")
    raise SystemExit(0)


def done(name):
    print(f"OK {name}")
