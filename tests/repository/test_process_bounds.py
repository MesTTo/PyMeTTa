"""Purpose: bound every process this repository starts, past its starter.

`subprocess.run(timeout=)` is enforced in the PARENT's wait loop. Kill the
parent and nothing enforces it, and sessions here are killed routinely: two
swipl children spawned by a repository runner survived from 2026-09-01 to
2026-09-03, spinning at 100% for 122 CPU-hours between them, because the only
bound on them lived in a process that was gone.

Assumes:
  - GNU `timeout` is on PATH. conftest refuses loudly when it is not, rather
    than spawning unbounded, so this suite cannot pass in the configuration
    the bound is missing from.
Guarantees:
  - the bound is OBSERVED rather than asserted from the code that installs it:
    a child is asked what its own parent is, which is the one question a
    parent-side timeout cannot answer with `timeout`
  - the mechanism is exercised against a real orphan, because "the wrapper is
    in the argv" and "the wrapper reaps an orphan" are different claims and
    only the second is the guarantee
Fails when: someone replaces the wrapper with a parent-side kill in a
  `finally`, which passes an ordinary run and changes nothing about an
  orphan. That is the fix this test exists to reject.
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
import time

import pytest


def test_a_process_this_suite_starts_reports_a_wrapper_as_its_parent() -> None:
    """Ask the child, not the code that spawned it."""
    done = subprocess.run(
        ["sh", "-c", "ps -o args= -p $PPID"],
        capture_output=True, text=True, timeout=60, check=True,
    )
    assert "timeout" in done.stdout, (
        "a child this suite started names "
        f"{done.stdout.strip()!r} as its parent, not a `timeout` wrapper, so "
        "its bound is being kept by pytest and dies with pytest. See "
        "conftest._bound_children_to_a_wrapper."
    )


@pytest.mark.skipif(shutil.which("timeout") is None, reason="needs GNU timeout")
def test_an_orphaned_child_is_reaped_by_its_own_wrapper() -> None:
    """The guarantee itself: kill the parent, and the child still ends.

    The parent here is a `sh` that spawns the wrapper and exits immediately,
    so the wrapper is orphaned the moment it starts. Nothing is waiting on it,
    which is exactly the state that let the two 122-CPU-hour children run.
    """
    marker = f"metta-bound-probe-{os.getpid()}"
    spawner = subprocess.Popen(
        ["sh", "-c",
         f"timeout -k 1 2 sh -c 'while :; do :; done  # {marker}' & exit 0"],
    )
    spawner.wait(timeout=30)

    def alive() -> list[str]:
        listing = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True,
                                 text=True, timeout=60, check=True).stdout
        return [line for line in listing.splitlines()
                if marker in line and "ps -eo" not in line]

    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if not alive():
            return
        time.sleep(0.25)

    survivors = alive()
    for line in survivors:
        with contextlib.suppress(Exception):
            os.kill(int(line.split()[0]), signal.SIGKILL)
    pytest.fail(
        "an orphaned child outlived its 2-second bound: "
        f"{survivors}. The bound is not in a process that shares the child's "
        "fate."
    )

