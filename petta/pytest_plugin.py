"""Purpose: the shipped pytest fixtures every project testing against PeTTa
otherwise rewrites: an engine and a scratch space, registered as a pytest11
entry point so a user's test file starts at the assert.
Guarantees:
  - scratch_space drops its space after the test, so a suite's churn reuses
    names instead of growing the engine's module table [tested
    test_shipped_plugin_provides_the_fixtures]
Decides:
  - the fixtures use pytest's own override rule: a conftest defining metta
    or scratch_space wins over these, which is how a project customizes
    the boot (a petta_path, a preloaded library) without a plugin knob
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

from .space import MeTTa


@pytest.fixture(scope="session")
def metta() -> MeTTa:
    """The engine, one per session, because there is one per process."""
    return MeTTa()


@pytest.fixture()
# The parameter NAME is pytest's own fixture-injection mechanism.
def scratch_space(metta: MeTTa):  # pylint: disable=redefined-outer-name
    """A fresh anonymous space per test, dropped afterwards: stored
    state is isolated; registrations stay process-wide, exactly as
    new_space documents."""
    with metta.new_space() as space:
        yield space
