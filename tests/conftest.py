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

from metta import Space

# The twins moved to extensions/python/examples/language-feature-examples/,
# out of this directory, so pytest no longer reaches them from here and the
# ignore that used to sit at this line is gone with them. What replaced it is
# an exclusion in repository/test_examples.py, which is the runner that now
# globs the folder they landed in.

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

    Read BEFORE and after, and blame only what this test added. Reading only
    afterwards blamed whichever test ran next after the real leaker, which is
    the very mis-attribution the paragraph above describes: it sent two
    separate readers to test_bounds.py, whose three tests use the scoped form
    and pass in isolation.
    """

    def bounds_in_force():
        # A pragma set to 0 bounds nothing: the engine documents zero as
        # "selects the default" for max-stack-depth, and
        # examples/ch14-seeing-your-program/01-time_and_pragmas.metta ends
        # by teaching exactly that. Reporting it would blame a chapter for
        # demonstrating the engine-wide form it exists to explain.
        try:
            return {
                row["Key"]: row["Value"]
                for row in janus_swi.query("metta_pragma(Key, Value)")
                if row["Value"] != 0
            }
        except janus_swi.PrologError:  # the engine was never started by this test
            return None

    before = bounds_in_force()
    yield
    after = bounds_in_force()
    if after is None:
        return
    added = sorted(key for key, value in after.items() if before.get(key) != value)
    assert not added, (
        f"this test left {added} set engine-wide; use "
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
    return repo_root / "extensions" / "python" / "tests" / "fixtures" / "dummy.metta"


@pytest.fixture(scope="session")
def metta(metta_path):
    """Return the process home space on the repository runtime.

    The suite drives the engine's own ``&self`` deliberately: scratch spaces
    minted from it fall back to ``&self`` for equations, and many tests
    define there and evaluate in a child. Context isolation has its own
    pins (test_metta_contexts_are_isolated and the ownership group).
    """
    os.environ.setdefault("METTA_PATH", metta_path)
    return Space(metta_path=metta_path)
