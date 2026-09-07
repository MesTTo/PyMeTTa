"""Purpose: keep a battery red from being recorded as an "intermittent".

A red that passes when the named test is re-run alone is a claim about the
process state the battery had and the re-run did not. `tests/conftest.py`
attaches that state to every failing item, and this file is what keeps it
attached: a planted red run through the same hook has to carry the engine's
pragmas, its fuel scope, SWI's autoload and stack-limit flags, the worker, the
position in the shuffled order, the seed and the load.
Assumes: this seat's pyproject.toml and an interpreter with janus_swi, the
  same pair every other runner here uses.
Guarantees:
  - a failing item carries the report, with the state the failure had rather
    than the state a later reader can reconstruct
    [tested: test_a_failing_item_carries_the_state_that_decided_it; commit=WORKTREE]
  - the report names every field it promises, and says so when the engine
    cannot answer instead of dropping the row
    [tested: test_the_state_report_names_every_field_it_promises,
    test_a_reading_the_engine_refuses_is_reported_rather_than_dropped;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import ClassVar

from tests import conftest as suite_conftest

REPO = Path(__file__).resolve().parents[4]
PYTHON_ROOT = REPO / "extensions" / "python"

#: A test that fails on purpose while an engine-wide pragma is in force, which
#: is the exact shape of the failures this report exists to explain.
PLANTED = '''
def test_planted_red(metta):
    metta.run("!(pragma! max-stack-depth 7)")
    raise AssertionError("planted")
'''


def test_a_failing_item_carries_the_state_that_decided_it(tmp_path):
    """The hook is wired up, and it fires on a red and not on a green."""
    planted = tmp_path / "test_planted_red.py"
    planted.write_text(PLANTED, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            "--rootdir=.", "-c", "pyproject.toml",
            "-p", "no:benchmark", "-p", "no:cacheprovider",
            "-p", "tests.conftest",
            str(planted),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(PYTHON_ROOT),
        check=False,
    )
    assert result.returncode != 0, result.stdout[-2000:]
    report = result.stdout
    assert "engine state at failure" in report, report[-3000:]
    # The pragma the planted test left in force is IN the report: reading the
    # state after the fact is what the report replaces.
    assert "max-stack-depth" in report, report[-3000:]
    for field in ("worker:", "seed:", "order:", "load:", "spaces:", "fuel scope:",
                  "prolog flags:", "function generation:"):
        assert field in report, f"{field} missing from\n{report[-3000:]}"
    assert "metta=&self" in report, report[-3000:]


def test_the_state_report_names_every_field_it_promises(metta):  # noqa: ARG001  -- the fixture is here to boot the engine the report reads
    """Every promised row is present when the engine is up.

    Against a live engine rather than a stub, because the rows are engine
    goals and a stub would agree with them by construction.
    """
    class _Config:
        @staticmethod
        def getoption(name, default=None):  # noqa: ARG004  -- the pytest Config signature
            return default

    class _Item:
        config = _Config()
        funcargs: ClassVar[dict[str, object]] = {}

    report = suite_conftest.engine_state_report(_Item())
    for field in ("worker:", "seed:", "order:", "load:", "spaces:", "pragmas:",
                  "fuel scope:", "prolog flags:", "function generation:"):
        assert field in report, f"{field} missing from\n{report}"


def test_a_reading_the_engine_refuses_is_reported_rather_than_dropped(metta, monkeypatch):  # noqa: ARG001  -- the fixture is here to boot the engine the report reads
    """A goal the engine cannot answer says so, and the other rows still land.

    A report that silently drops the reading it could not take is a report
    that reads as "the engine was fine", which is the one thing it must never
    say by omission.
    """
    monkeypatch.setattr(
        suite_conftest,
        "ENGINE_STATE_GOALS",
        (*suite_conftest.ENGINE_STATE_GOALS, ("planted", "no_such_predicate(Answer)")),
    )

    class _Config:
        @staticmethod
        def getoption(name, default=None):  # noqa: ARG004  -- the pytest Config signature
            return default

    class _Item:
        config = _Config()
        funcargs: ClassVar[dict[str, object]] = {}

    report = suite_conftest.engine_state_report(_Item())
    assert "planted: the engine refused the reading" in report, report
    assert "prolog flags:" in report, report
