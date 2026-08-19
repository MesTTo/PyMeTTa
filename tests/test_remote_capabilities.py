"""Purpose: which capabilities a RemoteSpace claims, and whether the wire it
speaks can actually carry them.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

import petta
from petta import S, V, remote
from petta.atoms import atom_from_wire
from petta.errors import PettaError


def _store_transport(store: list):
    """The four operations revision 1 of the wire defines, and no others."""

    def transport(operation: str, payload: dict) -> dict:
        if operation == "add":
            store.append(atom_from_wire(payload["atom"]))
            return {}
        if operation == "remove":
            atom = atom_from_wire(payload["atom"])
            if atom not in store:
                return {"removed": False}
            store.remove(atom)
            return {"removed": True}
        if operation in ("match", "atoms"):
            return {"atoms": [atom.to_wire() for atom in store]}
        raise AssertionError(f"the wire has no {operation} operation")

    return transport


def test_remote_space_claims_subscribe_only_if_the_channel_exists(metta):
    """A capability is a promise about a space, and subscribe promises that
    a watcher hears every change to it.

    SpaceProvider derives subscribe from add and remove, which is exactly
    right for a space whose every change goes through this process. A remote
    space is the one shape where that inference fails: its contents change on
    the server, which is the whole reason it is remote. Measured 2026-08-19
    against an attached space, a subscription accepted the pattern, delivered
    the one atom this process wrote, and delivered nothing at all for the
    atom the server added. So the watcher heard only the changes it had
    already made itself.

    The condition, stated positively rather than assumed: the wire has four
    operations and none of them carries an event. That is what the test name
    means by "only if", so it is asserted here rather than left to the
    refusal message to imply.
    """
    space = "&remote-caps"
    store: list = []
    provider = remote.attach(metta, space, _store_transport(store))
    try:
        # The channel does not exist: the wire carries four operations and
        # asking it for a fifth is a hole, not a slow path.
        with pytest.raises(AssertionError, match="no subscribe operation"):
            _store_transport(store)("subscribe", {})

        # So the capability is not claimed, for any event direction.
        for on in ("add", "remove", "both"):
            assert not provider.can_run("subscribe", on=on), f"claimed subscribe on={on}"
        assert not provider.can_run("subscribe")

        # And the refusal says what is missing, not just that it is missing.
        with pytest.raises(PettaError, match="no event") as caught:
            metta.space(space).subscribe(S.fact(V.x), lambda event: None)
        assert "bridge" in str(caught.value), "the refusal names no way forward"

        # Withdrawing it is surgical: what the wire does carry still works.
        for capability in ("match", "enumerate", "add", "remove"):
            assert provider.can_run(capability), capability
        metta.run(f"!(add-atom {space} (fact one))")
        assert store == [S.fact(S.one)]
        assert metta.run(f"!(match {space} (fact $x) $x)") == [[S.one]]

        # bridge() the other way round is the supported route across, and it
        # only ever needed add and remove on the target.
        local = metta.new_space()
        rule = petta.bridge(local, S.alarm(V.zone), metta.space(space), S.fact(V.zone))
        try:
            local.add(S.alarm(S.kitchen))
            assert S.fact(S.kitchen) in store
        finally:
            rule.cancel()
            local.drop()
    finally:
        metta.unregister_space(space)
