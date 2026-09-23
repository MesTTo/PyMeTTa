"""Purpose: set up the suite's import path and load its two harness plugins.

`_workspace.on_path()` is the one implementation of the path; this is the hook
that runs it before a test module imports a member. The benchmark drivers call
the same function for the same reason, since they run as their own processes.
`tests._xdist_scheduling` keeps a replaced xdist worker from wedging the run,
and `tests._progress_timeout` times each item by its progress, not the clock.

Assumes: this file's directory is importable, which pytest's `pythonpath = ["."]`
  provides and which this file also arranges for itself, because a conftest is
  imported before that setting is applied in some invocations.
Guarantees:
  - `import metta_<name>` works anywhere in this suite [tested:
    ext/metta-pandas/tests/test_pandas.py; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - every run under this rootdir loads `tests._xdist_scheduling` and
    `tests._progress_timeout` [tested: test_the_suite_loads_the_restart_scheduler,
    test_the_suite_times_items_by_progress; commit=WORKTREE]
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

# Here and nowhere lower: pytest honours `pytest_plugins` only in the top-level
# conftest, and this one is loaded by every run beneath it, a run narrowed to
# one file included
# [source: https://docs.pytest.org/en/stable/deprecations.html#pytest-plugins-in-non-top-level-conftest-files].
pytest_plugins = ["tests._xdist_scheduling", "tests._progress_timeout"]
