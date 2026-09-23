"""Purpose: time a test item by its PROGRESS rather than by the wall clock, so
the per-item timeout names a stuck item and not one a loaded box slowed.

pytest-timeout's thread method arms a `threading.Timer` for `timeout` seconds
of wall time. On a box that is never unloaded, a CPU-bound item's wall time
stretches with everyone else's work: test_door_rows.py's planted-change sweep
takes 154.64s at a load of about 15 [measured 2026-09-24, battery 76], and
under the gate's own load a worker running that file was killed at 900s
inside metta/doors/_analysis.py [measured 2026-09-23, battery 7], which is a
stuck-item verdict on an item that was working. Its
maintainer declines a CPU-time clock
[source: https://github.com/pytest-dev/pytest-timeout/issues/157], and CPU
time alone would never fire on a deadlock, which spends none.

Progress is the wall time less the time the item's own thread spent RUNNABLE
BUT WAITING for a CPU, which the kernel counts per thread as `run_delay` in
/proc/<pid>/task/<tid>/schedstat. Contention drops out and nothing else does:
a thread blocked on a lock, a pipe or a child still accrues progress, so a
deadlocked item is still stopped after `timeout` seconds of it.

The timer comes in through pytest-timeout's own `pytest_timeout_set_timer`
hook, which exists for alternative timer implementations, so its settings,
its `timeout` marker, its header and its debugger detection stay its own, and
when the budget is spent it runs pytest-timeout's own `timeout_timer`: the
same dump of every thread's stack and the same os._exit(1).
Assumes:
  - the thread that calls pytest_timeout_set_timer is the thread that runs
    the item, which is pytest-timeout's contract for both of its hooks
    [source: pytest_timeout.py 2.4.0, pytest_runtest_protocol and
    pytest_runtest_call]
Guarantees:
  - a CPU-bound item that a competing process holds to half a CPU is timed
    by the work it did, and an item that blocks is still stopped after its
    budget [tested: test_a_contended_item_is_timed_by_its_progress,
    test_a_blocked_item_is_still_stopped; commit=WORKTREE]
Fails when:
  - the item's work runs on OTHER threads while its own thread waits for
    them: their contention is not subtracted, so the bound tightens back
    toward the wall clock for that item.
  - the kernel exposes no per-thread schedstat: the delay reads as zero and
    progress is the wall clock, exactly pytest-timeout's own timer.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the file contract is one continuous header, not summary-and-body prose

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest


def _run_delay(tid: int) -> float:
    """Seconds thread `tid` of this process has spent waiting on a run queue.

    The second field of schedstat, in nanoseconds
    [source: https://docs.kernel.org/scheduler/sched-stats.html,
    /proc/<pid>/schedstat]. Zero where the kernel does not expose it, which
    turns progress back into the wall clock rather than into a guess.
    """
    try:
        return int(Path(f"/proc/self/task/{tid}/schedstat").read_text(encoding="ascii").split()[1]) / 1e9
    except (OSError, IndexError, ValueError):
        return 0.0


class ProgressTimer:
    """Call `expire` once thread `tid` has made `budget` seconds of progress.

    It sleeps for the budget still unspent, which is the least wall time in
    which the budget can run out, since progress never outpaces the wall
    clock; on waking it reads the delay again and sleeps for what remains, so
    a contended item costs a few wakeups and no polling.
    """

    def __init__(self, budget: float, tid: int, expire: Any, name: str) -> None:
        self._budget = budget
        self._tid = tid
        self._expire = expire
        self._cancelled = threading.Event()
        self._thread = threading.Thread(target=self._watch, name=name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancelled.set()
        self._thread.join()

    def _watch(self) -> None:
        started = time.monotonic()
        waited = _run_delay(self._tid)
        remaining = self._budget
        while not self._cancelled.wait(remaining):
            progress = (time.monotonic() - started) - (_run_delay(self._tid) - waited)
            remaining = self._budget - progress
            if remaining <= 0:
                self._expire()
                return


@pytest.hookimpl(tryfirst=True, optionalhook=True)
def pytest_timeout_set_timer(item: pytest.Item, settings: Any) -> bool | None:
    """Arm a progress timer where pytest-timeout would arm a wall-clock one.

    Only for the thread method, the one this suite configures; the signal
    method is left to pytest-timeout. Optional because a run without
    pytest-timeout never calls it, and pytest refuses an unknown hook
    otherwise.
    """
    if settings.method != "thread":
        return None
    # Imported here, so a run without pytest-timeout can still load this plugin.
    from pytest_timeout import timeout_timer

    timer = ProgressTimer(
        settings.timeout,
        threading.get_native_id(),
        lambda: timeout_timer(item, settings),
        f"pytest_timeout progress {item.nodeid}",
    )
    # pytest-timeout's own cancel hook calls this, as it does for its timers.
    item.cancel_timeout = timer.cancel
    timer.start()
    return True
