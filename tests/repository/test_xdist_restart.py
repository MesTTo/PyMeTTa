"""Purpose: hold the pytest lane's worker-restart path to what it promises.

extensions/python/tests/_xdist_scheduling.py carries pytest-xdist master's restart
fixes, and PR #1371's, for the scope schedulers while the installed release
lacks them. These tests hold three things about it: the patched schedulers
pass the scenarios upstream wrote for those fixes, a real run with a crashing
worker finishes and runs the crashed test once, and the override is still
needed, which is its removal condition written as a test.
Guarantees:
  - every scope scheduler xdist ships passes the restart scenarios with
    RestartSafe ahead of it [tested: test_the_restart_scheduler_passes_every_scenario;
    commit=WORKTREE]
  - a worker that dies under --dist loadfile is replaced, the rest of its file
    runs on the replacement, and the test it died on is reported once
    [tested: test_a_crashed_worker_is_replaced_without_wedging_or_rerunning;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys

import pytest
import xdist
from xdist.scheduler import LoadScopeScheduling

from metta._roots import workspace
from tests import _xdist_scheduling

SEAT = workspace() / "extensions" / "python"


def _scope_schedulers() -> list[type]:
    """LoadScopeScheduling and every subclass xdist itself ships, from xdist."""
    pending, found = [LoadScopeScheduling], []
    while pending:
        scheduling = pending.pop()
        if scheduling.__module__.startswith("xdist."):
            found.append(scheduling)
            pending.extend(scheduling.__subclasses__())
    return sorted(found, key=lambda scheduling: scheduling.__name__)


@pytest.mark.parametrize("scheduling", _scope_schedulers(), ids=lambda scheduling: scheduling.__name__)
def test_the_restart_scheduler_passes_every_scenario(scheduling):
    """With RestartSafe ahead of it, no scope scheduler has a restart defect."""
    assert _xdist_scheduling.defects(_xdist_scheduling.patched(scheduling)) == frozenset()


def test_the_installed_xdist_still_needs_the_restart_scheduler():
    """The override's removal condition, which fails the day it is met."""
    remaining = _xdist_scheduling.defects(LoadScopeScheduling)
    assert remaining, (
        f"pytest-xdist {xdist.__version__}'s own LoadScopeScheduling passes "
        f"every restart scenario, so it carries #1323, #1327 and #1371: delete "
        f"extensions/python/tests/_xdist_scheduling.py, its pytest_plugins line in "
        f"extensions/python/conftest.py, this file, and the note citing it in "
        f"extensions/python/test.sh"
    )


def test_the_suite_loads_the_restart_scheduler(pytestconfig):
    """The rootdir conftest registers the plugin for this very run."""
    assert pytestconfig.pluginmanager.has_plugin("tests._xdist_scheduling")


def test_a_crashed_worker_is_replaced_without_wedging_or_rerunning(tmp_path):
    """One worker, and a test that kills it with the rest of its file queued.

    Upstream's own reproduction for #1371 [source: pytest-xdist PR #1371 head
    2b820f4b76e3, testing/acceptance_test.py::TestNodeFailure::test_loadfile_crashed_worker].
    On 3.8.0 alone the run wedges on the replacement, and with #1328 alone it
    ends "5 failed, 2 passed" with test_after never run; here the crash fails
    once and everything else passes. The child gets its own ini and no
    autoloaded plugins, so it cannot inherit this repository's configuration.
    """
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_a.py").write_text(
        "def test_pass_1(): pass\ndef test_pass_2(): pass\n", encoding="utf-8"
    )
    (tmp_path / "test_b.py").write_text(
        "import os\ndef test_crash(): os._exit(1)\ndef test_after(): pass\n", encoding="utf-8"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(SEAT), environment.get("PYTHONPATH")])
    )
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        run = subprocess.run(
            [
                sys.executable, "-m", "pytest", "-v",
                "-p", "xdist.plugin", "-p", "tests._xdist_scheduling",
                "-n", "1", "--dist", "loadfile",
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            # The bound upstream's reproduction uses for the same run.
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as wedged:
        # Captured output arrives as bytes here whatever `text` said.
        output = (wedged.stdout or b"").decode(errors="replace")
        pytest.fail(f"the run wedged on the replacement worker:\n{output}")
    assert "replacing crashed worker gw0" in run.stdout, run.stdout
    # handle_crashitem's own report of it [source: xdist/dsession.py:436, 3.8.0].
    assert "worker 'gw0' crashed while running 'test_b.py::test_crash'" in run.stdout, run.stdout
    assert "1 failed, 3 passed" in run.stdout, run.stdout
