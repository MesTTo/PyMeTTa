"""Purpose: telling a failed write apart from a watcher that failed after a
write succeeded, which a caller deciding whether to retry has to do.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import pytest

from petta import EngineError, PettaError, S, SubscriberError, V
from petta.foreign import Adder, Enumerable, SpaceProvider


class _ReadOnly(SpaceProvider, Adder, Enumerable):
    """A space that refuses every write. Nothing it is handed is stored."""

    def __init__(self) -> None:
        self.store: list = []

    def add(self, atom) -> None:  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        msg = "the store is read-only today"
        raise RuntimeError(msg)

    def atoms(self):
        return iter(self.store)


def test_a_watcher_failure_is_distinguishable_from_a_failed_write(metta):
    """The two arrived as the same thing, and they call for opposite moves.

    A subscription callback runs inside the write that triggered it, so its
    exception comes back out through the writer. Measured 2026-08-19, both
    of these reached the caller as `EngineError: Python '<Type>': <text>`,
    the same class and the same message template:

        a provider that refused the write        RuntimeError, nothing stored
        a watcher that raised after the write     ValueError, the atom stored

    Retrying the first is right. Retrying the second takes the count from 1
    to 2 and leaves it there, because a space is a multiset and no later
    write undoes the copy.

    So the test asserts the distinction is carried by the TYPE rather than
    by the sentence, and that the fields say which subscription, which atom
    and which direction.
    """
    read_only = _ReadOnly()
    refusing = "&read-only-store"
    metta.register_space(read_only, refusing)
    try:
        with pytest.raises(EngineError) as refused:
            metta.run(f"!(add-atom {refusing} (fact one))")
        assert not isinstance(refused.value, SubscriberError)
        assert read_only.store == []
    finally:
        metta.unregister_space(refusing)

    space = metta.new_space()
    try:

        def angry(event):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
            msg = "the watcher is broken"
            raise ValueError(msg)

        watcher = space.subscribe(S.fact(V.x), angry)
        try:
            with pytest.raises(SubscriberError) as caught:
                space.add(S.fact(S.one))
        finally:
            watcher.cancel()

        failure = caught.value
        assert failure.subscription is watcher
        assert failure.atom == S.fact(S.one)
        assert failure.space == space.space_name
        assert failure.action == "add"
        assert isinstance(failure.__cause__, ValueError)
        assert "the watcher is broken" in str(failure)
        # It says the write stands, and the space agrees.
        assert "applied" in str(failure)
        assert len(space.query(S.fact(V.q))) == 1
        # Still a PettaError, so nothing that caught it before stops doing so.
        assert isinstance(failure, PettaError)

        # The removal direction reads the same way, and the removal stands too.
        removing = space.subscribe(S.fact(V.x), angry, on="remove")
        try:
            with pytest.raises(SubscriberError) as removed:
                space.remove(S.fact(S.one))
        finally:
            removing.cancel()
        assert removed.value.action == "remove"
        assert space.query(S.fact(V.q)) == []
    finally:
        space.drop()
