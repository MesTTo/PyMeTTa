"""Purpose: give a replaced xdist worker the restart handling pytest-xdist
master has and 3.8.0 lacks, through xdist's own scheduler hook.

The lane replaces a worker that dies (--max-worker-restart in
extensions/python/test.sh), and pytest-xdist 3.8.0's LoadScopeScheduling,
which --dist loadfile, loadscope and loadgroup all run, mishandles the
replacement three ways:

  - #1323. remove_node puts back every unit the dead worker held, finished
    ones included, so a replacement can be sent a unit with nothing pending
    and idle for ever. Fixed on master by 25282ab9215b.
  - #1327. schedule() gives a node joining after the first distribution one
    unit. A worker does not start a test until it holds the next one or is
    told to shut down, so a replacement handed a single-test unit waits in
    remote.py's torun.get() and the controller waits on it: the lane runs to
    bounded.sh's 3600 s ceiling and reports nothing. Fixed on master by
    eba6a4475eb8 (PR #1328).
  - #1371. remove_node leaves the test the worker died on pending, so each
    replacement runs it again and dies on it in turn until the restart budget
    is spent, although handle_crashitem has already reported it failed.
    LoadScheduling pops the crashed item for this reason; PR #1371 (open,
    head 2b820f4b76e3) does the same here.

Assumes:
  - LoadScopeScheduling keeps 3.8.0's collection, nodes, workqueue,
    assigned_work, _pending_of, _reschedule and _assign_work_unit, which
    RestartSafe is written against. `defects` checks that behaviourally rather
    than by version: `restart_safe` refuses a run whose patched class still
    fails a scenario
    [source: https://github.com/pytest-dev/pytest-xdist/blob/eba6a4475eb8697fc476357ff54d7b8b948781cf/src/xdist/scheduler/loadscope.py;
    https://github.com/pytest-dev/pytest-xdist/pull/1371/commits/2b820f4b76e3212b523e45411e358bff42638bff].
Guarantees:
  - under --dist loadfile, loadscope and loadgroup, a node that joins late is
    sent two pending tests whenever two are queued, no node is sent a unit with
    none, and the test a worker died on is not run again
    [tested: test_the_restart_scheduler_passes_every_scenario,
    test_a_crashed_worker_is_replaced_without_wedging_or_rerunning;
    commit=8442aabdd634cb561d5eca2e55b58d69d4698a8a]
Fails when:
  - the installed xdist's own class passes every scenario in `defects`. The
    override then stands aside and
    test_the_installed_xdist_still_needs_the_restart_scheduler fails, naming
    this file, its registration in extensions/python/conftest.py and the note
    citing it in extensions/python/test.sh for deletion.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the file contract is one continuous header, not summary-and-body prose

from __future__ import annotations

import functools
from collections.abc import Generator, Sequence
from types import SimpleNamespace
from typing import Any

import pytest

#: The upstream issue each scenario in `defects` detects.
REQUEUES_FINISHED_UNITS = 1323
LEAVES_A_LATE_NODE_ONE_TEST = 1327
RERUNS_THE_CRASHED_TEST = 1371


class RestartSafe:
    """LoadScopeScheduling's restart path as master and PR #1371 have it.

    Placed ahead of the class xdist chose, so `super()` reaches that class and
    its `_split_scope` stays whatever loadfile, loadscope or loadgroup says.
    """

    collection: list[str] | None
    workqueue: Any
    assigned_work: dict[Any, dict[str, dict[str, bool]]]
    registered_collections: dict[Any, list[str]]
    nodes: list[Any]

    def schedule(self) -> None:
        """Give a node that joins after the first distribution a second pass.

        A replacement holds nothing before its first `_reschedule`, and one
        pass hands it one unit, which may be a single test it cannot start
        (#1327) [source: pytest-xdist eba6a4475eb8 LoadScopeScheduling.schedule].
        """
        rescheduling = self.collection is not None
        super().schedule()  # type: ignore[misc]
        if rescheduling:
            for node in self.nodes:
                self._reschedule(node)  # type: ignore[attr-defined]

    def remove_node(self, node: Any) -> str | None:
        """Take a node out, putting back only the work it had not finished.

        Master's body verbatim with PR #1371's one line, marked below: the
        crashed test is marked complete before the requeue, so the filter that
        drops finished units (#1323) also drops a unit whose only pending test
        was the crashed one
        [source: pytest-xdist eba6a4475eb8 LoadScopeScheduling.remove_node;
        PR #1371 head 2b820f4b76e3].
        """
        workload = self.assigned_work.pop(node)
        if not self._pending_of(workload):  # type: ignore[attr-defined]
            return None

        # The node crashed, identify test that crashed
        for work_unit in workload.values():
            for nodeid, completed in work_unit.items():
                if not completed:
                    crashitem = nodeid
                    # PR #1371: handle_crashitem reports it failed; running it
                    # again only crashes the replacement in turn.
                    work_unit[nodeid] = True
                    break
            else:
                continue
            break
        else:
            # Upstream's text, verbatim, named rather than written inline so the
            # ruff gate needs no suppression for it.
            msg = "Unable to identify crashitem on a workload with pending items"
            raise RuntimeError(msg)

        # Make uncompleted work units available again
        for scope, work_unit in workload.items():
            if any(not completed for completed in work_unit.values()):
                self.workqueue[scope] = work_unit

        for node in self.assigned_work:  # noqa: PLR1704  -- upstream's loop variable, kept verbatim
            self._reschedule(node)  # type: ignore[attr-defined]

        return crashitem

    def _assign_work_unit(self, node: Any) -> None:
        """Assign a work unit to a node, refusing one with nothing pending.

        Master's body verbatim: a unit with no pending test would leave its
        node idle for ever, so it raises instead (#1323)
        [source: pytest-xdist 25282ab9215b LoadScopeScheduling._assign_work_unit].
        """
        assert self.workqueue

        # Grab a unit of work
        scope, work_unit = self.workqueue.popitem(last=False)

        # Keep track of the assigned work
        assigned_to_node = self.assigned_work.setdefault(node, {})
        assigned_to_node[scope] = work_unit

        # Ask the node to execute the workload
        worker_collection = self.registered_collections[node]
        nodeids_indexes = [
            worker_collection.index(nodeid)
            for nodeid, completed in work_unit.items()
            if not completed
        ]
        if not nodeids_indexes:
            # Raise since this is an internal error that may result in a hanging worker
            # See #1323
            msg = "Trying to assign a work unit with no pending items to a node"
            raise RuntimeError(msg)

        node.send_runtest_some(nodeids_indexes)


class _Node:
    """What a scope scheduler touches on a WorkerController, recording its sends.

    [source: pytest-xdist testing/test_dsession.py MockNode]
    """

    def __init__(self, name: str) -> None:
        self.sent: list[int] = []
        self.shutting_down = False
        # _check_nodes_have_same_collection names every node pair by it.
        self.gateway = SimpleNamespace(id=name)

    def send_runtest_some(self, indices: Sequence[int]) -> None:
        self.sent.extend(indices)

    def shutdown(self) -> None:
        self.shutting_down = True


class _Options:
    loadscopereorder = False


class _Config:
    """What a scope scheduler reads from a config: the node count and the
    reorder switch, which is off so the queue keeps collection order.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

    option = _Options()

    def __init__(self, nodes: int) -> None:
        self._tx = [f"{nodes}*popen"]

    def getvalue(self, name: str) -> list[str]:
        if name != "tx":
            raise KeyError(name)
        return self._tx


def _requeue_defects(scheduling: type, log: Any) -> set[int]:
    """Upstream's test_remove_node_does_not_requeue_the_crashed_test, as a probe.

    Two nodes share six two-test files; the first finishes its first unit, then
    dies in the next. Afterwards no unit may be queued or held with nothing
    pending (#1323), and the test it died on may be pending nowhere (#1371).
    """
    sched = scheduling(_Config(2), log)
    first, second = _Node("first"), _Node("second")
    collection = [f"test_{name}.py::test_{index}" for name in "abcdef" for index in (1, 2)]
    for node in (first, second):
        sched.add_node(node)
    for node in (first, second):
        sched.add_node_collection(node, collection)
    sched.schedule()
    finished = next(iter(sched.assigned_work[first]))
    for nodeid in list(sched.assigned_work[first][finished]):
        sched.mark_test_complete(first, collection.index(nodeid))
    crashed = sched.remove_node(first)
    units = [*sched.workqueue.values(), *sched.assigned_work[second].values()]
    found = set()
    if any(all(unit.values()) for unit in units):
        found.add(REQUEUES_FINISHED_UNITS)
    if any(unit.get(crashed) is False for unit in units):
        found.add(RERUNS_THE_CRASHED_TEST)
    return found


def _topup_defects(scheduling: type, log: Any) -> set[int]:
    """Upstream's test_node_is_topped_up_until_it_can_report, as a probe.

    Two nodes take the two three-test files; a third joins while single-test
    files are queued and must be sent two tests, since a worker cannot start
    its last test without a next one (#1327).
    """
    sched = scheduling(_Config(2), log)
    early = [_Node("first"), _Node("second")]
    collection = [
        *(f"test_{name}.py::test_{index}" for name in "ab" for index in (1, 2, 3)),
        *(f"test_{name}.py::test_1" for name in "cde"),
    ]
    for node in early:
        sched.add_node(node)
    for node in early:
        sched.add_node_collection(node, collection)
    sched.schedule()
    queued = sum(list(unit.values()).count(False) for unit in sched.workqueue.values())
    late = _Node("late")
    sched.add_node(late)
    sched.add_node_collection(late, collection)
    sched.schedule()
    return {LEAVES_A_LATE_NODE_ONE_TEST} if len(late.sent) < min(2, queued) else set()


def defects(scheduling: type) -> frozenset[int]:
    """The upstream issues a scope scheduler class still has, by running it.

    Cost: two schedulers over twelve and nine stand-in tests, no processes;
    microseconds, paid once per session. Their log is disabled, since a
    scheduler built without one prints every decision to stderr.
    """
    # Imported here, as below, so a run without xdist can still load this plugin.
    from xdist.remote import Producer

    quiet = Producer("restart-probe", enabled=False)
    return frozenset(_requeue_defects(scheduling, quiet) | _topup_defects(scheduling, quiet))


@functools.cache
def patched(scheduling: type) -> type:
    """`scheduling` with RestartSafe ahead of it, one class per scheduler."""
    return type(scheduling.__name__, (RestartSafe, scheduling), {"__module__": __name__})


def restart_safe(scheduler: Any, config: pytest.Config, log: Any) -> Any:
    """The scheduler xdist chose, or its class with RestartSafe ahead of it
    while that class still has a defect RestartSafe removes.
    """  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose
    from xdist.scheduler import LoadScopeScheduling

    scheduling = type(scheduler)
    if not issubclass(scheduling, LoadScopeScheduling) or not defects(scheduling):
        return scheduler
    remaining = defects(patched(scheduling))
    if remaining:
        msg = (
            f"pytest-xdist's {scheduling.__name__} still fails the restart "
            f"scenarios for upstream issues {sorted(remaining)} with "
            f"extensions/python/tests/_xdist_scheduling.py's RestartSafe ahead of it, "
            f"so this xdist no longer has the internals that override was "
            f"written against; port RestartSafe to it, or delete the override "
            f"if the release carries #1323, #1327 and #1371"
        )
        raise pytest.UsageError(msg)
    return patched(scheduling)(config, log)


@pytest.hookimpl(wrapper=True, optionalhook=True)
def pytest_xdist_make_scheduler(config: pytest.Config, log: Any) -> Generator[None, Any, Any]:
    """Adapt whichever scheduler xdist, or another plugin, chose.

    Optional because a run without xdist never calls it, and pytest refuses an
    unknown hook otherwise [source: https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html#optionally-using-hooks-from-3rd-party-plugins].
    """
    return restart_safe((yield), config, log)
