"""Purpose: put this workspace's extension packages on the path for the suite.

`_workspace.on_path()` is the one implementation; this is the hook that runs it
before a test module imports a member. The benchmark drivers call the same
function for the same reason, since they run as their own processes.

Assumes: this file's directory is importable, which pytest's `pythonpath = ["."]`
  provides and which this file also arranges for itself, because a conftest is
  imported before that setting is applied in some invocations.
Guarantees:
  - `import metta_<name>` works anywhere in this suite [tested:
    ext/metta-pandas/tests/test_pandas.py; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _workspace import on_path  # noqa: E402  -- the path is arranged just above

on_path()
