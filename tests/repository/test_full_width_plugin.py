"""Purpose: prove a pytest run decides its own width and holds the machine by it.

tests/_full_width.py decides once the run knows its tests. Each case here runs
a child pytest over stub test files in a world of its own: a private lock, a
private report file, and nproc told the machine has 32 processors, so the
share is 4 wherever this runs and nothing here can touch the machine's lock.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from metta._roots import seat, workspace

SEAT = seat()
ROOT = workspace()
LIBRARY = ROOT / "tools" / "full_width.sh"
#: A runner's refused invocation, where a claim's is 125: a runner in a gate
#: lane exits 125 only for a prerequisite the machine lacks
#: (tests/checks/full_width.py, RUNNER_REFUSED).
REFUSED = 1


def _world(directory: Path, files: int, body: str = "def test_it():\n    pass\n",
           ) -> tuple[dict[str, str], Path, Path]:
    """FILES stub test files, and the environment, lock and report of their world."""
    (directory / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    for index in range(files):
        (directory / f"test_{index}.py").write_text(body, encoding="utf-8")
    lock, report = directory / "full-width.lock", directory / "report"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(SEAT), environment.get("PYTHONPATH")])
    )
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["METTA_FULL_WIDTH_LOCK"] = str(lock)
    environment["METTA_FULL_WIDTH_REPORT"] = str(report)
    environment["OMP_NUM_THREADS"] = "32"
    return environment, lock, report


def _pytest(directory: Path, environment: dict[str, str], *options: str,
            ) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "tests._full_width", *options],
        cwd=directory, env=environment, capture_output=True, text=True, timeout=120,
        check=False,
    )


def _decisions(report: Path) -> list[list[str]]:
    """Each decision the run reported, as its word and what decided it."""
    if not report.is_file():
        return []
    return [line.split("\t")[:2] for line in report.read_text(encoding="utf-8").splitlines()]


XDIST = ("-p", "xdist.plugin", "-n", "4", "--dist", "loadfile")


def test_the_suite_decides_its_width(pytestconfig):
    """The rootdir conftest registers the width plugin for this very run."""
    assert pytestconfig.pluginmanager.has_plugin("tests._full_width")


def test_a_run_over_one_share_of_files_holds_the_machine(tmp_path):
    """Four workers over four files is W 4, one share: the controller holds the lock."""
    environment, lock, report = _world(tmp_path, 4)
    run = _pytest(tmp_path, environment, *XDIST)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "4 passed" in run.stdout, run.stdout
    assert _decisions(report) == [["full", "W=4 share=4"]]
    record = lock.read_text(encoding="utf-8").split("\t")
    assert "-m pytest" in record[3], record


def test_a_run_below_one_share_holds_nothing(tmp_path):
    """Four workers over three files is W 3: light, and nothing is held or recorded."""
    environment, lock, report = _world(tmp_path, 3)
    run = _pytest(tmp_path, environment, *XDIST)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "3 passed" in run.stdout, run.stdout
    assert _decisions(report) == [["light", "W=3 share=4"]]
    assert not lock.exists() or not lock.read_text(encoding="utf-8")


def test_a_run_beside_a_holder_runs_no_test(tmp_path):
    """A full-width run while another holds the machine ends 1, naming it, with no test run.

    The holder's PID is read from its record: this suite starts children
    through bounded.sh, so the process Popen names is the wrapper around it.
    """
    environment, lock, _report = _world(tmp_path, 4)
    holding = {key: value for key, value in environment.items()
               if key != "METTA_FULL_WIDTH_REPORT"}
    holder = subprocess.Popen(
        ["sh", "-c", '. "$1" && metta_full_width_claim /planted planted 2>/dev/null &&'
                     ' echo held && exec cat >/dev/null', "holder", str(LIBRARY)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=holding,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        holding_pid = lock.read_text(encoding="utf-8").split("\t")[0]
        run = _pytest(tmp_path, environment, *XDIST)
    finally:
        holder.kill()
        holder.wait()
    assert run.returncode == REFUSED, run.stdout + run.stderr
    assert "passed" not in run.stdout, run.stdout
    assert f"PID      {holding_pid}" in run.stderr, run.stderr


def test_a_run_without_xdist_claims_only_when_it_measures(tmp_path):
    """One process is W 1; a benchmark it times makes it a measurement all the same."""
    environment, lock, report = _world(tmp_path, 4)
    run = _pytest(tmp_path, environment)
    assert run.returncode == 0, run.stdout + run.stderr
    assert _decisions(report) == []
    assert not lock.exists() or not lock.read_text(encoding="utf-8")
    timed = tmp_path / "timed"
    timed.mkdir()
    environment, lock, report = _world(
        timed, 1, "def test_it(benchmark):\n    benchmark(lambda: None)\n")
    run = _pytest(timed, environment, "-p", "pytest_benchmark.plugin")
    assert run.returncode == 0, run.stdout + run.stderr
    assert _decisions(report) == [["full", "measures"]]
    disabled = _pytest(timed, environment, "-p", "pytest_benchmark.plugin", "--benchmark-disable")
    assert disabled.returncode == 0, disabled.stdout + disabled.stderr
    assert _decisions(report) == [["full", "measures"]], "a disabled benchmark decided again"


def test_a_measuring_driver_holds_the_machine(tmp_path):
    """benchmarks.decide_width("measures") holds the machine for the driver's own process."""
    environment, lock, report = _world(tmp_path, 0)
    run = subprocess.run(
        [sys.executable, "-c",
         "import os, benchmarks; print(benchmarks.decide_width('measures'), os.getpid())"],
        cwd=SEAT, env=environment, capture_output=True, text=True, timeout=120, check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    outcome, pid = run.stdout.split()
    assert outcome == "held", run.stdout
    assert lock.read_text(encoding="utf-8").split("\t")[0] == pid
    assert _decisions(report) == [["full", "measures"]]
