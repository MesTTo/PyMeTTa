"""Purpose: exercise a NATIVE space across generated operation histories.

The multiset laws themselves are `metta.testing.SpaceMachine`, exported for
anybody's provider, and this runs that machine rather than a second copy of it:
stored atoms, length, membership and exact queries follow a `Counter` after
every generated operation, removal subtracts ONE copy and reports whether one
was there, and a scoped write commits or is discarded with its scope. What this
file adds is the one law that is not general, the save and load round trip,
which no foreign provider is asked for.

Guarantees:
  - the exported machine passes over a native space at the suite's own step
    count [tested TestSpaceStateMachine]
  - text and fast saves load into a fresh space with the same multiset
    [tested TestSpaceStateMachine]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from collections import Counter
from tempfile import TemporaryDirectory

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from hypothesis.stateful import rule  # noqa: E402

from metta import Space, testing  # noqa: E402


class SpaceStateMachine(testing.SpaceMachine):
    """The exported machine over a native space, plus the native-only law.

    Save and load stay HERE rather than in the export because a foreign
    provider's store is its own and the engine's two image formats say nothing
    about it. Everything else this used to spell out is inherited.
    """

    def __init__(self):
        """Drive the exported machine over a fresh native space."""
        self._owner = Space()
        super().__init__(self._owner._new_space)
        self._temporary = TemporaryDirectory(prefix="metta-stateful-")

    @rule(save_format=st.sampled_from(("metta", "fast")))
    def save_load_round_trip(self, save_format):
        """A saved space loads into a fresh one holding the same multiset."""
        path = f"{self._temporary.name}/space.{save_format}"
        assert self.space.save(path, format=save_format) == sum(self.model.values())
        with self._owner._new_space() as loaded:
            loaded.load(path)
            assert Counter(loaded.atoms()) == self.model

    def teardown(self):
        """Remove the temporary directory, then release the space."""
        self._temporary.cleanup()
        super().teardown()


TestSpaceStateMachine = SpaceStateMachine.TestCase
TestSpaceStateMachine.settings = settings(
    max_examples=25,
    stateful_step_count=20,
    deadline=None,
)
