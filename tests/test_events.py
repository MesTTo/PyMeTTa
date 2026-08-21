"""Purpose: the event quartet, blackbox.

Subscribability as a declared seam capability, the public event stream the
shipped models fold over, the blocking Linda pair, and the reaction agenda.
Guarantees:
  - a context that declares event delivery serves subscriptions, bridges and
    reactions exactly as a native space does, and one that declares none
    refuses all three naming the missing capability
    [tested test_a_context_that_declares_events_serves_them_and_one_that_does_not_refuses]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

import petta
from petta import S, V
from petta.errors import PettaError
from petta.foreign import SpaceProvider, delivery_promise


class Dictionary(SpaceProvider):
    """A list-backed space with no promise at all about change events.

    Every method the write path needs and nothing more, which is exactly
    the shape the old derivation read as "subscribable".
    """

    def __init__(self) -> None:
        """Start empty."""
        self.stored: list = []

    def atoms(self):
        """Everything held, in arrival order."""
        return iter(self.stored)

    def add(self, atom) -> None:
        """Store one atom; a space is a multiset, so copies are kept."""
        self.stored.append(atom)

    def remove(self, atom) -> bool:
        """Drop one occurrence, answering whether anything went."""
        for index, held in enumerate(self.stored):
            if held == atom:
                del self.stored[index]
                return True
        return False


class Announcing(Dictionary):
    """The same store, plus the promise.

    Every change to it comes through this engine, so the engine's own write
    hooks are an exact event source for it.
    """

    def delivers(self) -> tuple[str, str]:
        """Every write, once, in write order."""
        return ("per-write-exactly", "ordered")


def test_a_context_that_declares_events_serves_them_and_one_that_does_not_refuses(metta):
    """P12.14: subscribability is a declared capability, not an inference.

    Both providers below implement add and remove, which is everything the
    old derivation looked at, so the old rule called both subscribable. One
    of them can actually deliver and the other cannot, and only the provider
    knows which: a store whose every change comes through this engine gets
    per-write-exactly from the engine's own write hooks, and one whose
    contents also change elsewhere gets nothing.

    So the declared one serves the three shipped library models, subscribe,
    bridge and reaction, exactly as a native space does; the silent one
    refuses all three, and the refusal names the missing capability rather
    than reporting a missing method it demonstrably has.
    """
    loud, quiet = Announcing(), Dictionary()
    metta.register_space(loud, "&ev-declared")
    metta.register_space(quiet, "&ev-silent")
    target = metta.new_space()
    try:
        # The promise is an ordinary declaration atom, so a MeTTa program
        # reads what the engine acts on.
        rows = metta.space("&petta").query(S.events(V.ctx, V.delivery, V.order))
        promises = {str(row.ctx): (str(row.delivery), str(row.order)) for row in rows}
        assert promises["&ev-declared"] == ("per-write-exactly", "ordered")
        assert "&ev-silent" not in promises
        assert delivery_promise(quiet) is None

        # Served: the three models, on the declared foreign space.
        seen: list = []
        subscription = metta.space("&ev-declared").subscribe(
            S.tick(V.n), seen.append
        )
        rule = petta.bridge(
            metta.space("&ev-declared"), S.tick(V.n), target, S.heard(V.n)
        )
        metta.declare_reaction(
            "&ev-declared", "(tick $n)", "(insert &ev-mirror (reacted $n))"
        )
        mirror = metta.space("&ev-mirror")
        try:
            metta.space("&ev-declared").add(S.tick(1))
            assert [event.bindings["n"] for event in seen] == [1]
            assert target.query(S.heard(V.n))
            assert mirror.query(S.reacted(V.n))
        finally:
            rule.cancel()
            subscription.cancel()

        # Refused: each of the three, naming what is missing.
        with pytest.raises(PettaError, match="declares no event capability"):
            metta.space("&ev-silent").subscribe(S.tick(V.n), seen.append)
        with pytest.raises(PettaError, match="declares no event capability"):
            petta.bridge(metta.space("&ev-silent"), S.tick(V.n), target)
        with pytest.raises(PettaError, match="events &ev-silent"):
            metta.declare_reaction(
                "&ev-silent", "(tick $n)", "(insert &ev-mirror (reacted $n))"
            )

        # The refusal is surgical: what the provider does implement still
        # works, so this is a withdrawn promise rather than a broken space.
        metta.space("&ev-silent").add(S.tick(2))
        assert S.tick(2) in quiet.stored
        assert metta.space("&ev-silent").query(S.tick(V.n))
    finally:
        metta.unregister_space("&ev-silent")
        metta.unregister_space("&ev-declared")


def test_a_native_space_needs_no_declaration_to_be_watched(metta):
    """The engine's own store is not a context making a promise.

    Every write into a native space runs metta_on_atom_added/2, so
    per-write-exactly and ordered are facts about this engine rather than
    assumptions about a provider, and explain says so without anything
    having been declared.
    """
    space = metta.new_space()
    seen: list = []
    subscription = space.subscribe(S.native(V.x), seen.append)
    try:
        space.add(S.native(S.one))
        assert [event.bindings["x"] for event in seen] == [S.one]
        explained = {
            str(item.head): item
            for item in metta.run(
                f"!(explain (match {space.space_name} (native $x) $x))"
            )[0][0].children
        }
        assert str(explained["events"].children[1]) == "per-write-exactly"
        assert str(explained["events"].children[2]) == "ordered"
    finally:
        subscription.cancel()
