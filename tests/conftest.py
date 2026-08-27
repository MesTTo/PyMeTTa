"""Purpose: provide the shared repository, runtime, and engine pytest fixtures.

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""


import importlib
import os
from pathlib import Path

import janus_swi
import pytest

from metta import MeTTa

# The twins are programs the coverage lane runs, not test modules; five of
# them carry example-derived names pytest would otherwise import at
# collection (a shape the corpus carried before the fourteen example
# renames). Ignoring the
# directory here is the one general fix a per-file rename cannot be: the
# lane derives each twin's path from its example's, so a twin renamed alone
# becomes an orphan the corpus check rejects.
collect_ignore = ["twins"]

try:
    from hypothesis import settings
except ModuleNotFoundError:
    pass
else:
    # A red example must be reproducible: every failure prints its
    # reproduction blob, and HYPOTHESIS_PROFILE=ci derandomizes whole
    # runs while the default keeps exploring fresh examples.
    settings.register_profile("metta", print_blob=True)
    settings.register_profile("ci", print_blob=True, derandomize=True)
    settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "metta"))


@pytest.fixture(autouse=True)
def _pragmas_are_not_left_set():
    """Fail the test that leaves an interpreter pragma set for every later one.

    `pragma!` writes ONE engine-wide setting. A bare
    `(pragma! max-stack-depth 20)` therefore outlives the MeTTa object that
    wrote it and silently bounds every evaluation that follows in the same
    process, which surfaces as an unrelated `(Error <n> StackOverflow)` in
    whichever test happens to run next on that xdist worker: the file order
    decides which one, so it moves between runs and reproduces in neither
    isolation nor a rerun. `with-pragma!` is the scoped form and restores on
    every exit path, including an exception.
    """
    yield
    try:
        left = sorted({row["Key"] for row in janus_swi.query("metta_pragma(Key, _)")})
    except janus_swi.PrologError:  # the engine was never started by this test
        return
    assert not left, (
        f"this test left {left} set engine-wide; use "
        "(with-pragma! ((<key> <value>)) <expr>) instead of a bare pragma!"
    )


@pytest.fixture(scope="session")
def repo_root():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def metta_module():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return importlib.import_module("metta")


@pytest.fixture(scope="session")
def metta_path(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return str(repo_root)


@pytest.fixture(scope="session")
def dummy_metta_path(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return repo_root / "bindings" / "python" / "tests" / "fixtures" / "dummy.metta"


@pytest.fixture(scope="session")
def metta(metta_path):
    """Return the default rich space on the repository runtime."""
    os.environ.setdefault("METTA_PATH", metta_path)
    return MeTTa(metta_path=metta_path).self
