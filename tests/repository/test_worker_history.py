"""Purpose: hold tests/_worker_history.py to what it promises.

Each worker's own order of items is kept beside the run's log, and a replay
runs one again. Each scenario runs a planted suite in a child pytest with its
own ini and no
autoloaded plugins, so it inherits nothing of this repository's configuration,
and every planted test appends its worker and node id to a truth file as it
runs: the histories are read against what the workers did, not against what
the plugin says they did.
Guarantees:
  - under xdist each worker's history names exactly the items it ran, in its
    order, each start followed by a finish carrying the item's outcome
    [tested 2026-09-29T23:52:41+10:00: test_each_worker_s_history_is_the_items_it_ran_in_order].
  - a crashed worker's history ends in the start of the item it died in
    [tested 2026-09-29T23:52:41+10:00: test_a_crashed_worker_s_history_ends_in_the_item_it_died_in].
  - the replay command a red's report prints runs that worker's history again
    in its order, and the replay records the same history
    [tested 2026-09-29T23:52:41+10:00: test_a_red_s_replay_command_runs_its_worker_s_history_again].
  - a replay runs its history's order and not the collection's, keeping each
    item once where it was first named, and refuses a history naming an item
    the run did not collect, naming every such item, and a run with workers
    [tested 2026-09-29T23:52:41+10:00: test_a_replay_runs_the_history_s_order_not_the_collection_s,
    test_a_replay_keeps_the_history_s_order_and_deselects_the_rest,
    test_a_replay_names_every_item_the_collection_lacks,
    test_a_replay_refuses_a_history_the_run_did_not_collect,
    test_a_replay_refuses_workers].
  - a pytest a test starts records nothing, and a run's log is the file its
    output goes to when nothing names one, while that name still reaches it
    [tested 2026-09-29T23:52:41+10:00: test_a_pytest_a_test_starts_records_nothing,
    test_the_log_is_the_file_the_run_s_output_goes_to].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta._roots import workspace
from tests import _worker_history

SEAT = workspace() / "extensions" / "python"

#: Each planted test writes the worker running it and its node id here, which
#: is what a history is checked against.
TRUTH = "truth.txt"

#: What a planted run keeps of this process's environment, everything else
#: set by name: a planted run is a run of its own, built from nothing as
#: tools/twin_coverage.py builds a measured child. Inherited, this test's own
#: run reached it: under xdist the worker's PYTEST_XDIST_WORKER named every
#: planted test's worker (gw1 in the gate of 2026-09-29, where each runs as
#: master), and a PYTEST_ADDOPTS or a coverage variable would reach it the same
#: way. The scratch variables keep its files where this run's are, and the
#: loader variables are what an interpreter here may need.
KEPT_ENVIRONMENT = ("HOME", "TMPDIR", "TMP", "TEMP", "LD_LIBRARY_PATH")

#: A test that records itself in the truth file, then does `{then}`.
BODY = '''
{decorator}def test_{name}({arguments}):
    with open({truth!r}, "a", encoding="utf-8") as truth:
        truth.write(os.environ.get("PYTEST_XDIST_WORKER", "master") + " " + request.node.nodeid + "\\n")
    {then}
'''

#: The report a planted red carries, from the plugin's own rows, the way
#: tests/conftest.py's state report carries them.
REPORTING_CONFTEST = '''
import pytest
from tests import _worker_history

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.sections.append(("history", "\\n".join(_worker_history.report(item))))
'''


def _plant(directory: Path, files: dict[str, list[tuple[str, str, str]]]) -> Path:
    """A suite of `files`, each a list of (name, parameter values or "", statement after recording)."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    truth = directory / TRUTH
    for filename, tests in files.items():
        source = ["import os", "import pytest"]
        for name, params, then in tests:
            source.append(BODY.format(
                decorator=f"@pytest.mark.parametrize('x', {params})\n" if params else "",
                name=name, arguments="request, x" if params else "request",
                truth=str(truth), then=then,
            ))
        (directory / filename).write_text("\n".join(source) + "\n", encoding="utf-8")
    return directory


def _environment(**overrides: str | None) -> dict[str, str]:
    environment = {name: os.environ[name] for name in KEPT_ENVIRONMENT if name in os.environ}
    environment |= {
        "PATH": os.pathsep.join((str(Path(sys.executable).parent), "/usr/bin", "/bin")),
        "PYTHONPATH": str(SEAT),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    for name, value in overrides.items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def _pytest(suite: Path, *arguments: str, environment: dict[str, str],
            stdout: object = subprocess.PIPE) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *arguments],
        cwd=suite, env=environment, stdout=stdout, stderr=subprocess.STDOUT, text=True,
        # The bound upstream's xdist reproductions use for runs of this size.
        timeout=120, check=False,
    )


def _histories(directory: Path) -> dict[str, list[dict]]:
    """Each history file in `directory`, by worker, as its header then its records.

    Every scenario here runs one session beside its log, so a worker named by
    two files is a second session in the directory, which is a failure.
    """
    found = {}
    for path in sorted(directory.glob("*.jsonl")):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# "), path
        header = json.loads(lines[0][2:])
        assert header["worker"] not in found, f"a second session in {directory}: {path.name}"
        found[header["worker"]] = [header, *(json.loads(line) for line in lines[1:])]
    return found


def _truth(suite: Path) -> dict[str, list[str]]:
    ran: dict[str, list[str]] = {}
    for line in (suite / TRUTH).read_text(encoding="utf-8").splitlines():
        worker, nodeid = line.split(" ", 1)
        ran.setdefault(worker, []).append(nodeid)
    return ran


def _starts(records: list[dict]) -> list[str]:
    return [record["nodeid"] for record in records[1:] if "finish" not in record]


#: Four files, ten items, for two workers, with a red, a skip and parametrized ids among them.
SUITE = {
    "test_alpha.py": [("one", "", "pass"), ("two", "", "pass"),
                      ("red", "", "assert False, 'planted'")],
    "test_beta.py": [("one", "", "pass"), ("skipped", "", "pytest.skip('planted')")],
    "test_gamma.py": [("p", "[1, 2, 3]", "pass")],
    "test_delta.py": [("one", "", "pass"), ("two", "", "pass")],
}
#: By entry-point name: pytest-randomly hands its seed to workers only when the
#: plugin named `xdist` is loaded, and `-p xdist.plugin` registers it under that
#: longer name, so every worker refused to configure
#: [source 2026-09-29T16:23:44+10:00: pytest_randomly/__init__.py:119-121 and 144-150,
#: pytest-randomly 5.0.0].
PLUGINS = ("-p", "xdist", "-p", "randomly", "-p", "tests._worker_history")


def test_the_suite_records_worker_histories(pytestconfig):
    """The rootdir conftest registers the plugin for this very run."""
    assert pytestconfig.pluginmanager.has_plugin("tests._worker_history")
    assert pytestconfig.pluginmanager.get_plugin(_worker_history.NAME) is not None


def test_each_worker_s_history_is_the_items_it_ran_in_order(tmp_path):
    """Two workers under loadfile: each file names that worker's items, in order."""
    suite = _plant(tmp_path / "suite", SUITE)
    log = tmp_path / "run.log"
    run = _pytest(suite, *PLUGINS, "-n", "2", "--dist", "loadfile", "-q",
                  environment=_environment(METTA_RUN_LOG=str(log)))
    assert run.returncode == 1, run.stdout
    histories = _histories(log.with_name("run.log.history"))
    truth = _truth(suite)
    assert set(histories) == set(truth), (histories.keys(), truth.keys())
    for worker, records in histories.items():
        header = records[0]
        assert header["worker"] == worker
        assert header["args"] == [*PLUGINS, "-n", "2", "--dist", "loadfile", "-q"]
        assert isinstance(header["seed"], int), header
        assert _starts(records) == truth[worker], (worker, records)
        # Every start is followed at once by its own finish.
        body = records[1:]
        for start, finish in zip(body[::2], body[1::2], strict=True):
            assert finish["nodeid"] == start["nodeid"] and finish["start"] == start["start"]
            assert finish["finish"] >= finish["start"]
    outcomes = {record["nodeid"]: record["outcome"] for records in histories.values()
                for record in records[1:] if "finish" in record}
    assert outcomes["test_alpha.py::test_red"] == "failed"
    assert outcomes["test_beta.py::test_skipped"] == "skipped"
    assert sum(len(ids) for ids in truth.values()) == len(outcomes) == 10
    assert "history: each process's items" in run.stdout, run.stdout


def test_a_crashed_worker_s_history_ends_in_the_item_it_died_in(tmp_path):
    """A worker that dies leaves the item it died in as its last line, started and unfinished."""
    suite = _plant(tmp_path / "suite", {
        "test_a.py": [("pass_1", "", "pass"), ("pass_2", "", "pass")],
        "test_b.py": [("crash", "", "os._exit(1)"), ("after", "", "pass")],
    })
    log = tmp_path / "run.log"
    run = _pytest(suite, "-p", "xdist", "-p", "tests._xdist_scheduling",
                  "-p", "tests._worker_history", "-n", "1", "--dist", "loadfile",
                  "-p", "no:randomly", environment=_environment(METTA_RUN_LOG=str(log)))
    assert "replacing crashed worker gw0" in run.stdout, run.stdout
    histories = _histories(log.with_name("run.log.history"))
    crashed = [worker for worker, records in histories.items()
               if "test_b.py::test_crash" in _starts(records)]
    assert len(crashed) == 1, histories
    last = histories[crashed[0]][-1]
    assert last == {"nodeid": "test_b.py::test_crash", "start": last["start"]}, last
    finished = [record["nodeid"] for records in histories.values()
                for record in records[1:] if "finish" in record]
    assert "test_b.py::test_crash" not in finished
    assert "test_b.py::test_after" in finished, histories


def test_a_red_s_replay_command_runs_its_worker_s_history_again(tmp_path):
    """The command a red's report prints replays its worker's history, which records it again."""
    suite = _plant(tmp_path / "suite", SUITE)
    (suite / "conftest.py").write_text(REPORTING_CONFTEST, encoding="utf-8")
    log = tmp_path / "run.log"
    run = _pytest(suite, *PLUGINS, "-n", "2", "--dist", "loadfile", "-q",
                  environment=_environment(METTA_RUN_LOG=str(log)))
    assert run.returncode == 1, run.stdout
    replay = re.search(r"^replay: (.*)$", run.stdout, re.MULTILINE)
    worker = re.search(r"^worker: (gw\d+)$", run.stdout, re.MULTILINE)
    history = re.search(r"^history: (\S+\.jsonl)$", run.stdout, re.MULTILINE)
    assert replay and worker and history, run.stdout
    order = re.search(r"^order: item (\d+) this process ran, after (.*)$", run.stdout,
                      re.MULTILINE)
    recorded = _histories(log.with_name("run.log.history"))[worker.group(1)]
    starts = _starts(recorded)
    assert order and starts[int(order.group(1)) - 1] == "test_alpha.py::test_red", run.stdout
    assert order.group(2) == (starts[int(order.group(1)) - 2] if int(order.group(1)) > 1
                              else "nothing before it")
    replay_log = tmp_path / "replay.log"
    (suite / TRUTH).unlink()
    again = subprocess.run(
        ["sh", "-c", replay.group(1)], env=_environment(METTA_RUN_LOG=str(replay_log)),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120, check=False,
    )
    assert again.returncode == 1, again.stdout
    replayed = _histories(replay_log.with_name("replay.log.history"))
    assert list(replayed) == ["master"], replayed
    assert _starts(replayed["master"]) == starts
    assert _truth(suite) == {"master": starts}
    assert f"{10 - len(starts)} deselected" in again.stdout, again.stdout


def test_a_replay_refuses_a_history_the_run_did_not_collect(tmp_path):
    """A history naming an item this run lacks is another run's, and is refused."""
    suite = _plant(tmp_path / "suite", {"test_a.py": [("one", "", "pass")]})
    history = tmp_path / "other.jsonl"
    history.write_text('# {"worker": "gw3"}\n{"nodeid": "test_a.py::test_one", "start": 0.1}\n'
                       '{"nodeid": "test_gone.py::test_x", "start": 0.2}\n', encoding="utf-8")
    run = _pytest(suite, "-p", "tests._worker_history", f"--replay-history={history}",
                  environment=_environment(METTA_RUN_LOG=""))
    assert run.returncode == pytest.ExitCode.USAGE_ERROR, run.stdout
    assert "test_gone.py::test_x" in run.stdout and "did not collect" in run.stdout, run.stdout


def test_a_replay_runs_the_history_s_order_not_the_collection_s(tmp_path):
    """A history crossing between files against the collection's order runs in the history's.

    A worker's own history cannot show this, since under loadfile a worker's
    order is the collection's, restricted to its files.
    """
    suite = _plant(tmp_path / "suite", {
        "test_a.py": [("one", "", "pass"), ("two", "", "pass")],
        "test_b.py": [("one", "", "pass"), ("two", "", "pass")],
    })
    order = ["test_b.py::test_two", "test_a.py::test_one", "test_b.py::test_one"]
    history = tmp_path / "h.jsonl"
    history.write_text("".join(json.dumps({"nodeid": nodeid, "start": 0.1}) + "\n"
                               for nodeid in order), encoding="utf-8")
    run = _pytest(suite, "-p", "tests._worker_history", f"--replay-history={history}",
                  environment=_environment(METTA_RUN_LOG=""))
    assert run.returncode == 0, run.stdout
    assert _truth(suite) == {"master": order}
    assert "1 deselected" in run.stdout, run.stdout


def test_a_replay_refuses_workers(tmp_path):
    """A replay under xdist workers would hand the history's files out again, so it is refused."""
    suite = _plant(tmp_path / "suite", {"test_a.py": [("one", "", "pass")]})
    history = tmp_path / "h.jsonl"
    history.write_text('{"nodeid": "test_a.py::test_one", "start": 0.1}\n', encoding="utf-8")
    run = _pytest(suite, "-p", "xdist", "-p", "tests._worker_history", "-n", "2",
                  f"--replay-history={history}", environment=_environment(METTA_RUN_LOG=""))
    assert run.returncode == pytest.ExitCode.USAGE_ERROR, run.stdout
    assert "pass -n 0" in run.stdout, run.stdout


def test_the_log_is_the_file_the_run_s_output_goes_to(tmp_path):
    """Unnamed, the log is standard output's file; a pipe keeps none and a red run says so."""
    suite = _plant(tmp_path / "suite", {"test_a.py": [("red", "", "assert False")]})
    output = tmp_path / "out.log"
    with output.open("w", encoding="utf-8") as out:
        filed = _pytest(suite, "-p", "tests._worker_history", environment=_environment(),
                        stdout=out)
    assert filed.returncode == 1
    histories = _histories(tmp_path / "out.log.history")
    assert list(histories) == ["master"]
    assert _starts(histories["master"]) == ["test_a.py::test_red"]
    piped = _pytest(suite, "-p", "tests._worker_history", environment=_environment())
    assert piped.returncode == 1
    assert "history: not recorded: this run's output is not a file" in piped.stdout, piped.stdout
    # A log deleted since it was opened, with a file of the name /proc gives a
    # deleted file planted beside it: that name no longer reaches the open
    # file, so nothing is kept beside either.
    doomed = tmp_path / "doomed.log"
    planted = tmp_path / "doomed.log (deleted)"
    with doomed.open("w", encoding="utf-8") as out:
        doomed.unlink()
        planted.write_text("", encoding="utf-8")
        gone = _pytest(suite, "-p", "tests._worker_history", environment=_environment(),
                       stdout=out)
    assert gone.returncode == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        ["suite", "out.log", "out.log.history", planted.name]
    )


def test_a_pytest_a_test_starts_records_nothing(tmp_path):
    """A test's own pytest inherits the run's environment and keeps no history in it."""
    nest = tmp_path / "nest"
    nest.mkdir()
    (nest / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (nest / "test_inner.py").write_text("def test_inner():\n    pass\n", encoding="utf-8")
    suite = _plant(tmp_path / "suite", {"test_outer.py": [("starts_a_pytest", "", (
        "import subprocess, sys\n"
        f"    with open({str(nest / 'child.log')!r}, 'w') as out:\n"
        "        subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', "
        f"'tests._worker_history', 'test_inner.py'], cwd={str(nest)!r}, stdout=out, "
        "stderr=subprocess.STDOUT, check=True)"
    ))]})
    log = tmp_path / "run.log"
    run = _pytest(suite, "-p", "tests._worker_history",
                  environment=_environment(METTA_RUN_LOG=str(log)))
    assert run.returncode == 0, run.stdout
    assert "1 passed" in (nest / "child.log").read_text(encoding="utf-8")
    assert not (nest / "child.log.history").exists()
    histories = _histories(tmp_path / "run.log.history")
    assert list(histories) == ["master"], histories
    assert _starts(histories["master"]) == ["test_outer.py::test_starts_a_pytest"]


def test_a_history_file_is_read_as_pytest_replay_writes_it(tmp_path):
    """Comments and blank lines are skipped, both records of an item named, and a bad line refused."""
    history = tmp_path / "h.jsonl"
    history.write_text(
        '# {"worker": "gw0"}\n\n// a comment\n'
        '{"nodeid": "a.py::t", "start": 0.1}\n'
        '{"nodeid": "a.py::t", "start": 0.1, "finish": 0.2, "outcome": "passed"}\n'
        '{"nodeid": "b.py::t[x y]", "start": 0.3}\n',
        encoding="utf-8",
    )
    assert _worker_history.recorded(history) == ["a.py::t", "a.py::t", "b.py::t[x y]"]
    history.write_text('{"nodeid": "a.py::t"}\nnot json\n', encoding="utf-8")
    with pytest.raises(pytest.UsageError, match=r"h\.jsonl:2 is not a history line"):
        _worker_history.recorded(history)


_ids = st.lists(st.text(alphabet="abcxyz:[]-_ ", min_size=1, max_size=6), unique=True, max_size=12)


@given(collected=_ids, data=st.data())
def test_a_replay_keeps_the_history_s_order_and_deselects_the_rest(collected, data):
    """For any collection and any history drawn from it, repeats included."""
    history = data.draw(st.lists(st.sampled_from(collected), max_size=20) if collected
                        else st.just([]))
    kept, rest = _worker_history.replay_order(collected, history, lambda nodeid: nodeid)
    assert kept == list(dict.fromkeys(history))
    assert rest == [nodeid for nodeid in collected if nodeid not in set(history)]
    assert sorted(kept + rest) == sorted(collected)


@given(collected=_ids, strangers=st.lists(st.text(alphabet="pq", min_size=1, max_size=3),
                                          min_size=1, max_size=3, unique=True),
       data=st.data())
def test_a_replay_names_every_item_the_collection_lacks(collected, strangers, data):
    """Every id the history names and the run did not collect is named, in the history's order."""
    known = data.draw(st.lists(st.sampled_from(collected), max_size=5) if collected
                      else st.just([]))
    history = data.draw(st.permutations([*known, *strangers]))
    with pytest.raises(LookupError) as refused:
        _worker_history.replay_order(collected, history, lambda nodeid: nodeid)
    assert refused.value.args[0] == [nodeid for nodeid in dict.fromkeys(history)
                                     if nodeid not in collected]
