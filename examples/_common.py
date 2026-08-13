"""Purpose: make petta importable from a repository checkout regardless of
the example's folder depth, point PETTA_PATH at that checkout, and provide
small helpers that make each example self-verifying rather than a printout
to trust.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import sys
from pathlib import Path


def _find_repo(start: Path) -> Path:
    """Find the repository by its Python project and engine library markers."""
    for candidate in start.resolve().parents:
        if (candidate / "python" / "pyproject.toml").is_file() and (
            candidate / "lib"
        ).is_dir():
            return candidate
    raise RuntimeError(f"cannot find the PeTTa repository above {start}")


REPO = _find_repo(Path(__file__))
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
