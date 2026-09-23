"""Purpose: hold the per-item timeout to measuring progress, not the wall clock.

extensions/python/tests/_progress_timeout.py times each item by its wall time
less the time its thread spent waiting for a CPU. These tests run a child
pytest with pytest-timeout and that plugin only, and show the contract's three
parts: an item slowed by a competitor for its CPU is not stopped for it, an
item that blocks still is, and a timeout inside an xdist worker still reports.
Guarantees:
  - a CPU-bound item needing 2s of CPU, sharing its only CPU with a spinning
    process so that it takes about twice that in wall time, passes a 3s
    budget, and the same item under pytest-timeout's own wall-clock timer does
    not [tested: test_a_contended_item_is_timed_by_its_progress;
    commit=51660d49c0291583453328617e311fad6ff028f0]
  - an item that sleeps is stopped once its budget has passed, with
    pytest-timeout's own Timeout report [tested:
    test_a_blocked_item_is_still_stopped; commit=51660d49c0291583453328617e311fad6ff028f0]
  - an item that times out inside an xdist worker leaves the Timeout banner,
    the line naming its progress and wall time, and its own frame in the run's
    output, where pytest-timeout's own timer in the same kind of worker leaves
    no banner [tested: test_a_timeout_in_a_worker_is_reported_in_the_run;
    commit=4af48475dca72577e5f482c7a757bde3b49db6bb]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import re
import subprocess
import sys

import pytest

from metta._roots import workspace

SEAT = workspace() / "extensions" / "python"

SPIN = """
import time

def test_spin():
    end = time.process_time() + 2.0
    while time.process_time() < end:
        pass
"""

SLEEP = """
import time

def test_sleep():
    time.sleep(30)
"""

# pytest-timeout's banner, one line of "+" around the word
# [source: pytest_timeout.py 2.4.0 timeout_timer, terminal.sep("+", title="Timeout")].
BANNER = re.compile(r"^\++ Timeout \++$", re.MULTILINE)


def _child(directory, source, budget, *plugins, cpu=None, workers=None):
    """Run one test file under a `budget`-second timeout in a child pytest
    that loads only pytest-timeout and the plugins named, in `workers` xdist
    workers when that is given.
    """  # noqa: D205  -- the helper contract is one continuous invariant, not summary-and-body prose
    directory.mkdir(parents=True)
    (directory / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (directory / "test_item.py").write_text(source, encoding="utf-8")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(SEAT), environment.get("PYTHONPATH")])
    )
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    command = [sys.executable, "-m", "pytest", "-q", "-p", "pytest_timeout"]
    for plugin in plugins:
        command += ["-p", plugin]
    if workers is not None:
        command += ["-p", "xdist.plugin", "-n", str(workers)]
    command += ["--timeout-method", "thread", "--timeout", str(budget)]
    if cpu is not None:
        command = ["taskset", "-c", str(cpu), *command]
    return subprocess.run(
        command, cwd=directory, env=environment, capture_output=True, text=True,
        # A bound on the child, far above both budgets, so a regression that
        # stops timing at all fails here rather than hanging the item.
        timeout=120, check=False,
    )


@pytest.fixture
def contended_cpu():
    """One CPU this process may use, with a process spinning on it throughout."""
    cpu = min(os.sched_getaffinity(0))
    spinner = subprocess.Popen(["taskset", "-c", str(cpu), sys.executable, "-c", "while True: pass"])
    try:
        yield cpu
    finally:
        spinner.kill()
        spinner.wait()


def test_a_contended_item_is_timed_by_its_progress(tmp_path, contended_cpu):
    """Waiting for a CPU is not progress, so a slowed item keeps its budget."""
    progress = _child(tmp_path / "progress", SPIN, 3, "tests._progress_timeout", cpu=contended_cpu)
    wall = _child(tmp_path / "wall", SPIN, 3, cpu=contended_cpu)
    assert progress.returncode == 0, progress.stdout[-2000:]
    assert "1 passed" in progress.stdout, progress.stdout[-2000:]
    # The control: the same item, the same CPU, pytest-timeout's own timer.
    assert wall.returncode != 0, wall.stdout[-2000:]
    assert "Timeout" in wall.stdout, wall.stdout[-2000:]


def test_the_suite_times_items_by_progress(pytestconfig):
    """The rootdir conftest registers the progress timer for this very run."""
    assert pytestconfig.pluginmanager.has_plugin("tests._progress_timeout")


def test_a_blocked_item_is_still_stopped(tmp_path):
    """Blocking is progress, so a stuck item is still named and ended."""
    run = _child(tmp_path / "blocked", SLEEP, 2, "tests._progress_timeout")
    assert run.returncode != 0, run.stdout[-2000:]
    assert "Timeout" in run.stdout, run.stdout[-2000:]
    assert "test_sleep" in run.stdout, run.stdout[-2000:]


def test_a_timeout_in_a_worker_is_reported_in_the_run(tmp_path):
    """A worker's stdout reaches nobody, so the report goes out on its stderr."""
    run = _child(tmp_path / "progress", SLEEP, 2, "tests._progress_timeout", workers=1)
    control = _child(tmp_path / "wall", SLEEP, 2, workers=1)
    output = run.stdout + run.stderr
    # handle_crashitem's own report of the worker's end [source: xdist/dsession.py:436, 3.8.0].
    assert "worker 'gw0' crashed while running 'test_item.py::test_sleep'" in run.stdout, output[-3000:]
    assert BANNER.search(output), output[-3000:]
    assert "test_item.py::test_sleep spent its 2s budget: " in output, output[-3000:]
    # The item's own frame, from the dump of every thread.
    assert ", in test_sleep" in output, output[-3000:]
    # The control: pytest-timeout's own timer, in the same kind of worker.
    assert not BANNER.search(control.stdout + control.stderr), (
        "pytest-timeout's own report now reaches the run from an xdist worker, so the "
        "stdout redirect in tests/_progress_timeout.py's _expire can go, and this control with it"
    )
