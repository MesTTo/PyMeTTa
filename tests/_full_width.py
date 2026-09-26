"""Purpose: decide a pytest run's width once it knows its tests, and hold the machine by it.

A pytest run is full-width by the rule every runner here decides by
(tools/full_width.sh, above metta_full_width_decide): W, the processes it runs
at once, reaches one lane's share, or it reads a load-sensitive quantity.
pytest knows W only after collection: with xdist it is the smaller of the
workers and the units the scheduler will hand them, files under
`--dist loadfile`, so the whole suite under `-n 16` is full-width and one file
under the same flags is not. So the decision is taken in the controller when
the first worker reports its collection, which xdist does before its scheduler
hands out any test [source 2026-09-27T01:22:13+10:00: pytest-xdist 3.8.0
dsession.py, worker_collectionfinish: the hook, then add_node_collection, then
schedule()].
Without xdist the run is one process, and it is full-width only when it
measures: under `--memray`, or with pytest-benchmark timing a test that asks
for its `benchmark` fixture.

A run refused exits 125 before any test, with the holder named on stderr.

Assumes: tests/checks/full_width.py in the workspace this seat sits in, and
  the Linux the lock itself assumes.
Guarantees:
  - an xdist run decides once, from its workers and its scheduler's own units,
    before the first test is scheduled, and a refused one ends 125 with no
    test run [tested 2026-09-27T02:16:58+10:00: tests/repository/test_full_width_plugin.py].
  - a run without xdist claims only when it measures
    [tested 2026-09-27T02:16:58+10:00: tests/repository/test_full_width_plugin.py].
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Any

import pytest

from _workspace import ROOT

sys.path.insert(0, str(ROOT / "tests" / "checks"))

import full_width

#: Whether this controller has decided, so later workers' collections are not asked again.
_decided = False


def _decide(width: int | str) -> None:
    global _decided
    _decided = True
    try:
        full_width.invocation(width)
    except SystemExit as stopped:
        pytest.exit("refused: another full-width run holds this machine"
                    if stopped.code == full_width.REFUSED
                    else f"the full-width decision failed, exit {stopped.code}",
                    returncode=stopped.code)


def _measures(config: pytest.Config, items: Sequence[pytest.Item]) -> bool:
    """Whether this run reads memory or a wall clock as its evidence.

    pytest-benchmark is loaded exactly when its option is registered, under
    whatever name the plugin was registered by.
    """
    if config.getoption("memray", default=False):
        return True
    return (config.getoption("benchmark_disable", default=True) is False
            and any("benchmark" in getattr(item, "fixturenames", ()) for item in items))


@pytest.hookimpl(trylast=True)
def pytest_collection_finish(session: pytest.Session) -> None:
    """Decide a run that collected in this process: no xdist, or a single process."""
    config = session.config
    if hasattr(config, "workerinput") or config.pluginmanager.getplugin("dsession"):
        return
    if _measures(config, session.items):
        _decide("measures")


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node: Any, ids: Sequence[str]) -> None:
    """Decide an xdist run from its workers and its scheduler's units, before any is scheduled."""
    if _decided:
        return
    config = node.config
    if config.getoption("memray", default=False):
        _decide("measures")
        return
    workers = len(config.getoption("tx") or ())
    scheduler = config.pluginmanager.getplugin("dsession").sched
    split = getattr(scheduler, "_split_scope", None)
    if config.getoption("dist") == "each":
        units = workers
    elif split is not None:
        units = len({split(nodeid) for nodeid in ids})
    else:
        units = len(ids)
    _decide(min(workers, units))
