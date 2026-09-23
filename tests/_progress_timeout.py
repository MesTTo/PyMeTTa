"""Purpose: time a test item by its PROGRESS rather than by the wall clock, so
the per-item timeout names a stuck item and not one a loaded box slowed.

pytest-timeout's thread method arms a `threading.Timer` for `timeout` seconds
of wall time. On a box that is never unloaded, a CPU-bound item's wall time
stretches with everyone else's work: test_door_rows.py's planted-change sweep
takes 154.64s at a load of about 15 [measured 2026-09-24, battery 76], and
under the gate's own load workers running that file died with nothing in the
lane to say why, after faulthandler's 180s dump had shown them still working
inside metta/doors/_analysis.py [measured 2026-09-19 and 2026-09-23, the
pytest lane's logs]. The wall-clock timeout ending an item that was working
is the likeliest reading, and those logs could not confirm it, for the reason
given below [assumed]. pytest-timeout's maintainer declines a CPU-time clock
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
same dump of every thread's stack and the same os._exit(1), after one line
saying which clock spent the budget, since the wall time can be many times it.

In an xdist worker that dump would reach nobody. timeout_timer writes through
the terminal writer, which is the worker's stdout, and execnet points a
worker's stdout at /dev/null [source: execnet 2.1.2 gateway_base.py
init_popen_io], so the lane read a timed-out worker as a crashed one and kept
no stack [tested: test_a_timeout_in_a_worker_is_reported_in_the_run's
control; commit=WORKTREE]. A worker's stderr is the controller's own, so in a
worker stdout becomes a copy of stderr just before the report. Nothing else
the worker writes changes route, since the process ends straight after.
Assumes:
  - the thread that calls pytest_timeout_set_timer is the thread that runs
    the item, which is pytest-timeout's contract for both of its hooks
    [source: pytest_timeout.py 2.4.0, pytest_runtest_protocol and
    pytest_runtest_call]
Guarantees:
  - a CPU-bound item that a competing process holds to half a CPU is timed
    by the work it did, and an item that blocks is still stopped after its
    budget [tested: test_a_contended_item_is_timed_by_its_progress,
    test_a_blocked_item_is_still_stopped; commit=51660d49c0291583453328617e311fad6ff028f0]
  - an item timed out inside an xdist worker leaves pytest-timeout's banner,
    the line naming its progress and wall time, and every thread's stack in
    the run's output [tested: test_a_timeout_in_a_worker_is_reported_in_the_run;
    commit=WORKTREE]
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

import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


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
    """Call `expire(progress, wall)` once thread `tid` has made `budget` seconds of progress.

    It sleeps for the budget still unspent, which is the least wall time in
    which the budget can run out, since progress never outpaces the wall
    clock; on waking it reads the delay again and sleeps for what remains, so
    a contended item costs a few wakeups and no polling.
    """

    def __init__(self, budget: float, tid: int, expire: Callable[[float, float], None], name: str) -> None:
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
            wall = time.monotonic() - started
            progress = wall - (_run_delay(self._tid) - waited)
            remaining = self._budget - progress
            if remaining <= 0:
                self._expire(progress, wall)
                return


def _expire(item: pytest.Item, settings: Any, progress: float, wall: float) -> None:
    """Report the spent budget where the run is read, then end the process.

    pytest-timeout's own timeout_timer writes the report and exits; this
    decides only where the report goes, and says which clock spent the budget.
    """
    # Imported here, so a run without pytest-timeout can still load this plugin.
    from pytest_timeout import is_debugging, timeout_timer

    # pytest-timeout's own test, under which it lets the item run on; checked
    # here too, or that case would announce a timeout that never comes.
    if not settings.disable_debugger_detection and is_debugging():
        return
    capture = item.config.pluginmanager.getplugin("capturemanager")
    if capture is not None:
        # timeout_timer's own first step, taken early so the line below is
        # written to the terminal rather than into the item's capture.
        capture.suspend_global_capture(in_=True)
    terminal = item.config.get_terminal_writer()
    # xdist's own test for a worker, spelled without importing xdist so a run
    # without it can still load this plugin
    # [source: pytest-xdist 3.8.0 xdist/plugin.py is_xdist_worker].
    if hasattr(item.config, "workerinput"):
        # Whatever the worker left buffered goes where it was going.
        terminal.flush()
        os.dup2(2, 1)
    terminal.line(
        f"{item.nodeid} spent its {settings.timeout:g}s budget: "
        f"{progress:.1f}s of progress in {wall:.1f}s of wall time"
    )
    timeout_timer(item, settings)


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
    timer = ProgressTimer(
        settings.timeout,
        threading.get_native_id(),
        lambda progress, wall: _expire(item, settings, progress, wall),
        f"pytest_timeout progress {item.nodeid}",
    )
    # pytest-timeout's own cancel hook calls this, as it does for its timers.
    item.cancel_timeout = timer.cancel
    timer.start()
    return True
