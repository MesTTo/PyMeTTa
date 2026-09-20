"""Purpose: bound every process this repository starts, past its starter.

`subprocess.run(timeout=)` is enforced in the PARENT's wait loop. Kill the
parent and nothing enforces it, and sessions here are killed routinely: two
swipl children spawned by a repository runner survived from 2026-09-01 to
2026-09-03, spinning at 100% for 122 CPU-hours between them, because the only
bound on them lived in a process that was gone. A deadline alone is not enough
either: on 2026-09-05 a hand-started swipl ran 7,540 seconds at 97.8% CPU, so
the bound also carries a LINK to the process that started it.

Assumes:
  - bounded.sh at the repository root, which conftest refuses loudly without,
    rather than spawning unbounded, so this suite cannot pass in the
    configuration the bound is missing from.
  - setpriv(1) for the owner link. Where it is absent the deadline still
    applies and the two reaping cases skip rather than lying.
Guarantees:
  - the bound is OBSERVED rather than asserted from the code that installs it:
    a child is asked what its own parent is, which is the one question a
    parent-side timeout cannot answer
    [tested: test_a_process_this_suite_starts_reports_a_wrapper_as_its_parent]
  - a child dies when the process that started it dies, within seconds, against
    an hour-long ceiling, so only the owner link can explain the death
    [tested: test_a_child_dies_with_the_process_that_started_it]
  - a child OUTLIVES the thread that spawned it, which is the property the
    parent-death signal's per-thread documentation puts at risk and which every
    xdist worker and ThreadPoolExecutor in this tree depends on
    [tested: test_a_child_outlives_the_thread_that_spawned_it]
  - the mechanism is exercised against a real orphan, because "the wrapper is
    in the argv" and "the wrapper reaps an orphan" are different claims and
    only the second is the guarantee
    [tested: test_an_orphaned_child_is_reaped_by_its_own_wrapper]
Fails when: someone replaces the wrapper with a parent-side kill in a
  `finally`, which passes an ordinary run and changes nothing about an
  orphan. That is the fix these tests exist to reject.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import threading
import time

import pytest

from metta._roots import workspace

REPO = workspace()
BOUNDED = REPO / "tools" / "bounded.sh"

#: A child that spins at 100% and refuses SIGTERM, so only an escalation to
#: SIGKILL ends it. The 2026-09-05 spinner needed one.
STUBBORN = "trap '' TERM; while :; do :; done"

needs_setpriv = pytest.mark.skipif(
    shutil.which("setpriv") is None,
    reason="the owner link is prctl(PR_SET_PDEATHSIG) through setpriv(1)",
)


def alive(pid: int) -> bool:
    """Whether the process still exists, without reaping anything."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def gone_within(pid: int, seconds: float) -> bool:
    """Wait for a pid to disappear, answering whether it did."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return not alive(pid)


def test_a_process_this_suite_starts_reports_a_wrapper_as_its_parent() -> None:
    """Ask the child, not the code that spawned it."""
    done = subprocess.run(
        ["sh", "-c", "ps -o args= -p $PPID"],
        capture_output=True, text=True, timeout=60, check=True,
    )
    assert "timeout" in done.stdout, (
        "a child this suite started names "
        f"{done.stdout.strip()!r} as its parent, not a deadline wrapper, so "
        "its bound is being kept by pytest and dies with pytest. See "
        "conftest._bound_children_to_a_wrapper."
    )


@needs_setpriv
def test_a_child_dies_with_the_process_that_started_it() -> None:
    """The guarantee the deadline cannot give, against an hour-long ceiling.

    The starter is a `sh` that spawns the bound child and waits. SIGKILLing it
    leaves nothing able to run a cleanup, which is the state a killed session
    is in, and the ceiling is an hour, so a death inside the window below is
    the owner link and can be nothing else.
    """
    marker = f"metta-owner-link-{os.getpid()}"
    starter = subprocess.Popen(
        ["sh", "-c",
         f'sh "{BOUNDED}" --ceiling 3600 --grace 5 '
         f"sh -c '{STUBBORN}  # {marker}' & echo $! > /dev/null; wait"],
    )
    child = _spinner_named(marker, born_within=30)
    starter.kill()
    starter.wait(timeout=30)
    assert gone_within(child, 25), (
        f"pid {child} outlived the process that started it, against a 3600s "
        "ceiling. Nothing links the command to its starter, so an orphan burns "
        "a core until the ceiling. See bounded.sh's outer rung."
    )


@needs_setpriv
def test_a_child_outlives_the_thread_that_spawned_it() -> None:
    """The false kill the parent-death signal's per-thread wording threatens.

    prctl(2) describes the signal as arriving when the THREAD that created the
    process exits. If that happened here, every child started from an xdist
    worker or from the ThreadPoolExecutor in tools/example_parity.py would be
    killed the moment that worker finished. Measured 2026-09-05 on Linux
    7.0.0-30-generic: it does not. This is what says so on the next kernel, and
    its remedy if it ever fails is an owner link held by a supervisor watching
    a pidfd rather than by prctl.
    """
    marker = f"metta-thread-owner-{os.getpid()}"
    box: list[subprocess.Popen] = []

    def spawn() -> None:
        box.append(subprocess.Popen(
            ["sh", str(BOUNDED), "--ceiling", "3600",
             "sh", "-c", f"{STUBBORN}  # {marker}"]))

    thread = threading.Thread(target=spawn)
    thread.start()
    thread.join()
    child = _spinner_named(marker, born_within=30)
    time.sleep(2.0)
    still_there = alive(child)
    with contextlib.suppress(Exception):
        os.killpg(os.getpgid(child), signal.SIGKILL)
    box[0].kill()
    box[0].wait(timeout=30)
    assert still_there, (
        "this kernel delivers the parent-death signal when the SPAWNING THREAD "
        "exits rather than when the process does, so every child started from "
        "a pool worker in this repository is killed the moment that worker "
        "finishes. bounded.sh's outer rung has to move from prctl to a "
        "supervisor watching the owner through a pidfd; see util-linux "
        "sys-utils/unshare.c."
    )


def test_an_orphaned_child_is_reaped_by_its_own_wrapper() -> None:
    """The deadline itself: kill the parent, and the child still ends.

    The parent here is a `sh` that spawns the wrapper and exits immediately,
    so the wrapper is orphaned the moment it starts. Nothing is waiting on it,
    which is exactly the state that let the two 122-CPU-hour children run.
    """
    marker = f"metta-bound-probe-{os.getpid()}"
    spawner = subprocess.Popen(
        ["sh", "-c",
         f'sh "{BOUNDED}" --ceiling 2 --grace 1 '
         f"sh -c 'while :; do :; done  # {marker}' & exit 0"],
    )
    spawner.wait(timeout=30)

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not _spinners_named(marker):
            return
        time.sleep(0.25)

    survivors = _spinners_named(marker)
    for line in survivors:
        with contextlib.suppress(Exception):
            os.kill(int(line.split()[0]), signal.SIGKILL)
    pytest.fail(
        "an orphaned child outlived its 2-second bound: "
        f"{survivors}. The bound is not in a process that shares the child's "
        "fate."
    )


def _spinners_named(marker: str) -> list[str]:
    """Every live process whose argv carries the marker, `pid args` per line."""
    listing = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True,
                             text=True, timeout=60, check=True).stdout
    return [line for line in listing.splitlines()
            if marker in line and "ps -eo" not in line]


def _spinner_named(marker: str, born_within: float) -> int:
    """The pid of the spinning child, once it exists.

    The marker sits in the child's own argv, so this reads the process the
    wrapper started rather than the wrapper: bounded.sh execs all the way down,
    which leaves the command's own argv in place and is what makes `ps`
    readable while a run is bounded.
    """
    deadline = time.monotonic() + born_within
    while time.monotonic() < deadline:
        for line in _spinners_named(marker):
            fields = line.split(maxsplit=1)
            if len(fields) == 2 and "sh -c" in fields[1]:
                return int(fields[0])
        time.sleep(0.05)
    missing = f"no process carrying {marker!r} ever started"
    raise AssertionError(missing)
