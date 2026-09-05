"""Purpose: provide the shared repository, runtime, and engine pytest fixtures.

Guarantees:
  - the source-tree suite registers ``metta.pytest_plugin`` when distribution
    metadata has not already done so, and never registers the module twice
    [tested: test_an_abandoned_watch_cancels_itself,
    test_source_tree_fixtures_coexist_with_installed_plugin_metadata;
    commit=993608c01049bcca7530931b680c416c81023543]
  - ``HYPOTHESIS_PROFILE=petta`` is a supported alias of the ordinary
    exploratory ``metta`` profile [tested: test_petta_profile_matches_metta;
    commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import importlib
import os
import subprocess
from pathlib import Path

import janus_swi
import pytest

from metta import Space
from metta import pytest_plugin as metta_pytest_plugin

#: The repository's one bound, which check.sh, test.sh, run.sh, engine/test.sh
#: and every seat's test.sh also call. It holds a deadline in a process of the
#: child's own AND links that child to the process that started it, so a killed
#: pytest reaps its children in milliseconds instead of leaving them to the
#: deadline: `subprocess.run(timeout=)` is enforced in the PARENT's wait loop
#: and stops enforcing when the parent does, which is how two swipl children
#: spawned by a repository runner survived from 2026-09-01 to 2026-09-03,
#: spinning at 100% for 122 CPU-hours between them.
BOUNDED = Path(__file__).resolve().parents[3] / "bounded.sh"


def _bound_children_to_a_wrapper() -> None:
    """Give every process this session starts a bound that outlives the session.

    Installed here rather than at each of the 63 call sites because the
    guarantee is a property of the SESSION, not of any one spawn, and a
    guarantee that has to be remembered 63 times is one that will be forgotten
    a 64th. `check.sh` gives the same guarantee to its lanes through `run()`
    and `bounded`; this is the same convention where pytest is driven directly,
    which is the case that convention did not reach.

    `bounded.sh` and not a `timeout` spelled out here, since 2026-09-05. Two
    copies of one policy had already drifted apart from the shell one, and the
    deadline alone was the whole bound: an orphaned child burned a core for the
    full hour rather than dying with its starter.

    Not `preexec_fn`. CPython documents it as unsafe in the presence of
    threads, and this suite runs under four xdist workers; the parent-death
    signal is armed inside `setpriv`, an already-exec'd single-threaded process,
    so no Python code runs between the fork and the exec.

    The other half of the old objection was that the kernel signals on the exit
    of the spawning THREAD rather than of the process, so a finished pool worker
    would kill a live child. It cannot happen here, for a reason stronger than
    the kernel's behaviour: every spawn this suite makes comes from the
    MainThread, in the controller and in each worker alike, and a CPython main
    thread does not exit before its process. Measured 2026-09-05 by recording
    `threading.current_thread()` at each `Popen` across a four-worker run: 43
    spawns over five processes, all `MainThread`, none exited at session
    finish. The kernel's behaviour is measured too and agrees --
    tests/shell/test_bounded_reaping.sh case 6 forks from a pthread, joins it,
    and finds the child alive, with PR_GET_PDEATHSIG read back as SIGKILL in
    the child and the process-death control dying in the same binary -- and
    that case is a GATE lane, so a kernel that changes it says so by name.

    `--owner` carries this process's pid, read BEFORE the fork, which is the
    only way the arming race closes completely: a wrapper that reads getppid()
    after it starts cannot tell a legitimate parent from a subreaper that
    adopted it, and comparing against 1 is wrong for both reasons
    [util-linux sys-utils/unshare.c opens a pidfd for the parent before forking
    for the same reason]. It goes in the ARGV rather than the environment so
    that a caller passing its own `env=` keeps exactly the environment it asked
    for; a wrapper that rewrites the environment is a wrapper that changes what
    it wraps.

    List-form commands only. Nothing in this tree passes `shell=True`, and a
    string command would have to be re-quoted to wrap, which is how a wrapper
    starts changing what it wraps.
    """
    if not BOUNDED.is_file():
        refusal = (
            f"this suite bounds the processes it starts through {BOUNDED}, "
            "and that file is not there. Without it a killed pytest leaves "
            "them running unbounded, which has already cost 122 CPU-hours. "
            "Restore it rather than removing this check."
        )
        raise RuntimeError(refusal)
    original = subprocess.Popen.__init__

    def bounded_init(self, args, *rest, **keywords):
        listed = isinstance(args, (list, tuple)) and args
        already = listed and str(BOUNDED) in [str(word) for word in args[:2]]
        if listed and not keywords.get("shell") and not already:
            args = ["sh", str(BOUNDED), "--owner", str(os.getpid()), *args]
        original(self, args, *rest, **keywords)

    subprocess.Popen.__init__ = bounded_init


def pytest_configure(config: pytest.Config) -> None:
    """Register the shipped fixtures only when entry-point discovery did not."""
    if not config.pluginmanager.is_registered(metta_pytest_plugin):
        config.pluginmanager.register(metta_pytest_plugin, "metta-source")
    _bound_children_to_a_wrapper()


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
    settings.register_profile("petta", parent=settings.get_profile("metta"))
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
    # Both readings, not only the key names. A scoped `with-pragma!` restores
    # by writing the PREVIOUS value back, so "appeared where there was nothing"
    # and "changed from one value to another" have different causes, and the
    # names alone cannot tell them apart. This fired once inside a full xdist
    # run on 2026-08-31 for max-stack-depth and has not reproduced since, so
    # the next occurrence carries its own evidence rather than another guess.
    assert not added, (
        f"this test left {added} set engine-wide; use "
        "(with-pragma! ((<key> <value>)) <expr>) instead of a bare pragma!. "
        f"before={ {key: before.get(key) for key in added} } "
        f"after={ {key: after[key] for key in added} }"
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
