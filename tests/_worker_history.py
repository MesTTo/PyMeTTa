"""Purpose: keep, beside a run's log, the order each process ran its items in,
and run one process's history again.

Under `--dist loadfile` xdist hands each file to whichever worker is free, so
which files a worker ran, and in what order, depends on timing, and neither
the seed nor the collection rebuilds it: a red seen once in a gate at seed
1024775652 passed in whole runs of both trees at that seed, and a replay of its
worker's history was the one input nobody had [the record,
i-metta-foreign-import-once, c-tip-arm-1024775652]. So the process that runs
an item writes it down before the item starts, and `--replay-history` runs one
process's history again, in its order, in one process.

The design and the file format are pytest-replay's, ported rather than
installed, since installing it adds a distribution every entry-point scan in
the shared environment then reads [the record, a-wh-install-pytest-replay]
[source 2026-09-29T16:02:30+10:00: https://github.com/ESSS/pytest-replay/blob/1cd6d049e45e0ee1522120b25c745a81f3d0f180/src/pytest_replay/__init__.py].
One JSON object a line: `{"nodeid", "start"}` as an item starts and
`{"nodeid", "start", "finish", "outcome"}` once it has finished, times in
seconds since the run began, and a line opening with `#` is a comment, so a
file replays under either tool. Each file opens with one comment holding the
run's wall-clock start, directory, arguments and seed, which place its times
against any other log and rebuild the replay command from the file alone. An
item with a start and no finish is the one its process was running when it
died, a timeout included, since pytest-timeout's thread method ends the
process.

The run's log is the file METTA_RUN_LOG names, none when that is empty, and
otherwise the file this process's standard output is, when that is a file.
The histories go in `<log>.history/`, one file a process that ran items,
`<HHMMSS>-<controller pid>-<worker>.jsonl`, the worker `master` for a run
without workers. The controller decides once and hands the decision to its
workers through `workerinput`, since execnet points a worker's standard output
at /dev/null, and it empties METTA_RUN_LOG in its own environment: a pytest a
test starts inherits that environment, PYTEST_XDIST_WORKER included, and
records nothing.

Assumes:
  - Linux's /proc/self/fd/1, to name the file standard output is. Without it
    a run records only under METTA_RUN_LOG.
  - pytest's capture is suspended at pytest_configure, so standard output is
    the run's own there rather than a capture file: _pytest/capture.py's
    pytest_load_initial_conftests suspends it before the first configure hook.
Guarantees:
  - each worker's file names, in order, exactly the items that worker ran, a
    crashed worker's ending in the start of the item it died in with no finish
    after it; a pytest a test starts writes nothing into the run's histories
    [tested 2026-09-29T16:37:35+10:00: tests/repository/test_worker_history.py].
  - `--replay-history FILE` over the run's own arguments runs FILE's items in
    FILE's order in one process and deselects the rest, so replaying a history
    records it again line for line; it refuses a history naming an item the
    run did not collect, and refuses to run under xdist workers
    [tested 2026-09-29T16:37:35+10:00: tests/repository/test_worker_history.py].
  - a failing item's report names its place in its process's run, the item its
    process ran before it, the history file and the command replaying it
    [tested 2026-09-29T16:37:35+10:00: tests/repository/test_failure_state_report.py].
Fails when:
  - the run's output goes to a terminal or a pipe and METTA_RUN_LOG is unset:
    nothing is recorded, and a red run's summary says so and names the
    variable.
  - METTA_RUN_LOG names a file whose directory cannot take `<log>.history/`:
    the run is refused before any test.
Owns resources: one append-only descriptor per process that runs items, on its
  own history file, opened at its first item and closed at
  pytest_unconfigure; an abandoned process's is closed by the kernel, and every
  line is already written, since each is one os.write with no buffer between.
Guarded by: nothing; each process writes only its own file.
"""  # noqa: D205  -- the file contract is one continuous header, not summary-and-body prose

from __future__ import annotations

import json
import os
import shlex
import stat
import sys
import time
from collections.abc import Callable, Generator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

#: The variable naming the file a run's output goes to; empty says the run keeps no log.
RUN_LOG = "METTA_RUN_LOG"
#: The name the history plugin is registered under, and the key the controller
#: hands its decision to a worker under.
NAME = "metta-worker-history"
#: Which outcome a finished item is recorded with when its phases differ, as
#: pytest-replay decides it: a failure outranks a skip, and a skip a pass.
RANK = {"passed": 0, "skipped": 1, "failed": 2}


def run_log() -> tuple[Path | None, str]:
    """The file this run's output goes to, or None and the reason there is none."""
    named = os.environ.get(RUN_LOG)
    if named is not None:
        if not named:
            return None, f"{RUN_LOG} is empty, which says this run keeps no log"
        return Path(named).resolve(), ""
    try:
        output = os.fstat(1)
        if not stat.S_ISREG(output.st_mode):
            return None, f"this run's output is not a file; set {RUN_LOG} to the log it goes to"
        target = Path("/proc/self/fd/1").readlink()
        named_file = target.stat()
    except OSError as unreadable:
        return None, f"this run's output could not be named ({unreadable}); set {RUN_LOG}"
    # The name /proc gives is the file's only while it still names the same
    # inode: a log deleted or replaced since it was opened is no place to put
    # anything beside.
    if (named_file.st_dev, named_file.st_ino) != (output.st_dev, output.st_ino):
        return None, f"this run's output, {target}, is no longer a file by that name; set {RUN_LOG}"
    return target, ""


def recorded(path: Path) -> list[str]:
    """The node ids a history names, in its order, from pytest-replay's line format."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as unreadable:
        msg = f"--replay-history: cannot read {path}: {unreadable}"
        raise pytest.UsageError(msg) from unreadable
    nodeids = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        # pytest-replay's comment rule, which its issue #70 settled.
        if not stripped or stripped.startswith(("#", "//")):
            continue
        try:
            nodeids.append(json.loads(stripped)["nodeid"])
        except (ValueError, KeyError, TypeError) as malformed:
            msg = f"--replay-history: {path}:{number} is not a history line: {stripped[:200]}"
            raise pytest.UsageError(msg) from malformed
    return nodeids


def replay_order[Item](items: Sequence[Item], nodeids: Sequence[str],
                       nodeid_of: Callable[[Item], str]) -> tuple[list[Item], list[Item]]:
    """The items `nodeids` names, in its order, and every other item, in theirs.

    A node id named twice runs once, where it was first named. Raises
    LookupError with the names the collection lacks, since a history replayed
    without one of its items is a different history.
    Cost: time linear in len(items) + len(nodeids); space, one dict of the items.
    """
    by_id = {nodeid_of(item): item for item in items}
    wanted = list(dict.fromkeys(nodeids))
    missing = [nodeid for nodeid in wanted if nodeid not in by_id]
    if missing:
        raise LookupError(missing)
    chosen = set(wanted)
    return [by_id[nodeid] for nodeid in wanted], [
        item for item in items if nodeid_of(item) not in chosen
    ]


class History:
    """One process's history, registered as the plugin that writes it.

    Every process of a run registers one, the controller's decision in hand:
    where the files go (or why nowhere), the run's session name, its
    wall-clock start and the monotonic instant the times count from.
    """

    def __init__(self, decision: dict[str, Any], worker: str) -> None:
        """Take the controller's `decision` for the process named `worker`."""
        self.decision = decision
        self.worker = worker
        self.ran = 0
        self.previous: str | None = None
        self.current: str | None = None
        self.outcome = "passed"
        self.began = 0.0
        self._descriptor: int | None = None

    @property
    def directory(self) -> Path | None:
        """Where the run's histories go, or None when it records none."""
        named = self.decision["directory"]
        return None if named is None else Path(named)

    @property
    def path(self) -> Path | None:
        """This process's history file, or None when the run records nothing."""
        directory = self.directory
        if directory is None:
            return None
        return directory / f"{self.decision['session']}-{self.worker}.jsonl"

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(self, node: Any) -> None:
        """Hand a worker the controller's decision, which its /dev/null output cannot make."""
        node.workerinput[NAME] = self.decision

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_protocol(self, item: pytest.Item) -> Generator[None, Any, Any]:
        """Record the item where it runs, which is only ever the process running it.

        The runtest protocol, not logstart: xdist's controller calls logstart
        again for every item a worker reports, and never runs the protocol.
        """
        if self.current is not None:
            self.previous = self.current
        self.ran += 1
        self.current = item.nodeid
        self.outcome = "passed"
        self.began = self._clock()
        self._write(item.config, {"nodeid": item.nodeid, "start": self.began})
        try:
            return (yield)
        finally:
            self._write(item.config, {"nodeid": item.nodeid, "start": self.began,
                                      "finish": self._clock(), "outcome": self.outcome})

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Keep the worst outcome the running item's phases report, and ignore any other item.

        The xdist controller is handed every worker's reports here, and runs none.
        """
        if report.nodeid == self.current and RANK[report.outcome] > RANK[self.outcome]:
            self.outcome = report.outcome

    def pytest_terminal_summary(self, terminalreporter: Any, exitstatus: int,
                                config: pytest.Config) -> None:
        """Name, on a red run, what repeats its order: the seed, and each process's history.

        pytest-randomly prints `Using --randomly-seed=N` through
        `pytest_report_header`, and every runner here passes `-q`, which
        shows no header at all [source 2026-09-29T16:44:07+10:00:
        _pytest/terminal.py TerminalReporter.showheader, pytest 9.1.1]. The
        seed repeats a run's shuffle, and under xdist no more than that, since
        which worker ran which file is timing's: three runs at one seed read
        three outcomes on two trees [source 2026-09-29T16:44:07+10:00:
        docs/journal/2026-09-07-the-gate-green-again.md, the runs at seed
        2964372231]. The histories are the rest.
        """
        if exitstatus == 0:
            return
        seed = config.getoption("randomly_seed", default=None)
        if seed is not None:
            terminalreporter.write_line(
                f"order: this run was shuffled; repeat it with --randomly-seed={seed}"
            )
        directory = self.directory
        if directory is None:
            terminalreporter.write_line(f"history: not recorded: {self.decision['reason']}")
        else:
            terminalreporter.write_line(
                f"history: each process's items, in the order it ran them, are in "
                f"{directory}/{self.decision['session']}-<worker>.jsonl; a failure's own "
                f"report names its file and the command replaying it"
            )

    def pytest_unconfigure(self) -> None:
        """Release the history file, if this process opened one."""
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None

    def _clock(self) -> float:
        return round(time.perf_counter() - self.decision["origin"], 3)

    def _write(self, config: pytest.Config, record: dict[str, Any]) -> None:
        path = self.path
        if path is None:
            return
        if self._descriptor is None:
            # O_EXCL: two processes given one name would interleave two
            # histories into one that neither ran.
            self._descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND,
                                       0o644)
            header = {"session": self.decision["session"], "worker": self.worker,
                      "started": self.decision["started"], "dir": self.decision["dir"],
                      "args": list(config.invocation_params.args),
                      "seed": config.getoption("randomly_seed", default=None)}
            self._line("# " + json.dumps(header))
        self._line(json.dumps(record))

    def _line(self, text: str) -> None:
        # One write a line, unbuffered, so a process that dies has written
        # every line it wrote. A regular file takes a short write only when
        # the disk fills, and then the loop writes the rest or raises.
        data = (text + "\n").encode()
        while data:
            data = data[os.write(self._descriptor, data):]  # type: ignore[arg-type]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the replay option."""
    parser.getgroup("history", "the order each process ran its items in").addoption(
        "--replay-history",
        metavar="HISTORY",
        type=Path,
        default=None,
        help="run only the items the history file HISTORY names, in its order, in this "
        "one process, over the run's own collection: pass the recorded run's arguments, "
        "its seed and -n 0",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register this process's history, decided once, in the controller."""
    workerinput = getattr(config, "workerinput", None)
    if workerinput is not None:
        config.pluginmanager.register(History(workerinput[NAME], workerinput["workerid"]), NAME)
        return
    if config.getoption("replay_history") is not None and config.getoption("numprocesses",
                                                                            default=None):
        msg = ("--replay-history runs one process's history in one process; "
               "pass -n 0 after the run's own arguments")
        raise pytest.UsageError(msg)
    log, reason = run_log()
    directory = None
    if log is not None:
        directory = log.with_name(log.name + ".history")
        try:
            directory.mkdir(exist_ok=True)
        except OSError as refused:
            msg = f"this run keeps its histories in {directory}, which cannot be made: {refused}"
            raise pytest.UsageError(msg) from refused
    # A pytest that a test starts inherits this environment, and keeps no
    # history of its own in this run's directory.
    os.environ[RUN_LOG] = ""
    decision = {
        "directory": None if directory is None else str(directory),
        "reason": reason,
        "session": f"{time.strftime('%H%M%S')}-{os.getpid()}",
        "started": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "origin": time.perf_counter(),
        "dir": str(config.invocation_params.dir),
    }
    config.pluginmanager.register(History(decision, "master"), NAME)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Replace the run's order with the history's, after every other plugin has ordered it."""
    path = config.getoption("replay_history")
    if path is None:
        return
    try:
        kept, rest = replay_order(items, recorded(path), lambda item: item.nodeid)
    except LookupError as missing:
        names = missing.args[0]
        msg = (f"--replay-history: {path} names {len(names)} item(s) this run did not "
               f"collect, so this is not the run that recorded it: {names[:5]}")
        raise pytest.UsageError(msg) from missing
    if rest:
        config.hook.pytest_deselected(items=rest)
    items[:] = kept


def report(item: Any) -> list[str]:
    """Where a failing item sat in its process's run, and how to run that again.

    Called from tests/conftest.py's state report with whatever item it has, a
    stub included, so every reading falls back to a row saying what is missing.
    """
    config = item.config
    worker = getattr(config, "workerinput", {}).get("workerid", "master")
    seed = config.getoption("randomly_seed", default=None)
    rows = [f"worker: {worker}", f"seed: {'unset' if seed is None else seed}"]
    manager = getattr(config, "pluginmanager", None)
    history = None if manager is None else manager.get_plugin(NAME)
    if history is None:
        return [*rows, "order: this run kept no history of the order its items ran in"]
    previous = "nothing before it" if history.previous is None else history.previous
    rows.append(f"order: item {history.ran} this process ran, after {previous}")
    path = history.path
    if path is None:
        return [*rows, f"history: not recorded: {history.decision['reason']}"]
    command = [sys.executable, "-m", "pytest", *config.invocation_params.args]
    if manager.has_plugin("xdist") or manager.has_plugin("xdist.plugin"):
        command += ["-n", "0"]
    if seed is not None:
        command.append(f"--randomly-seed={seed}")
    command.append(f"--replay-history={path}")
    return [*rows, f"history: {path}",
            f"replay: cd {shlex.quote(history.decision['dir'])} && {shlex.join(command)}"]
