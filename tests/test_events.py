"""Purpose: the event quartet, blackbox.

Subscribability as a declared seam capability, the public event stream the
shipped models fold over, the blocking Linda pair, and the reaction agenda.
Guarantees:
  - a context that declares event delivery serves subscriptions, bridges and
    reactions exactly as a native space does, and one that declares none
    refuses all three naming the missing capability
    [tested test_a_context_that_declares_events_serves_them_and_one_that_does_not_refuses]
  - each of the three shipped event models is reproducible as a fold over
    the public stream alone, with the same answers
    [tested test_subscribe_bridge_and_reaction_are_expressible_over_the_public_event_stream]
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

    Every write into a native space runs seam:atom_added/2, so
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


def test_subscribe_bridge_and_reaction_are_expressible_over_the_public_event_stream(metta):
    """P12.15: the stream is the primitive and the three models are folds.

    A third party gets one operation, `EventStream.fold`, and writes each of
    the shipped models with a different step: DELIVER for subscribe, WRITE
    for bridge, EVALUATE for a reaction. Each is run beside its shipped
    counterpart over the same writes and has to answer the same thing, which
    is what makes "a third party could have written these" checkable rather
    than asserted. Before this the tap was private and none of the three was
    reachable from outside the library.
    """
    stream = metta.events()
    source = metta.new_space()
    shipped_target, folded_target = metta.new_space(), metta.new_space()
    shipped_seen: list = []

    # DELIVER, subscribe's step: hand the event to a callback.
    shipped_subscription = source.subscribe(S.job(V.n), shipped_seen.append)
    folded_deliver = stream.fold(
        lambda held, event: [*held, event],
        space=source.space_name,
        pattern=S.job(V.n),
        state=[],
    )

    # WRITE, bridge's step: land the template's instantiation elsewhere.
    shipped_bridge = petta.bridge(source, S.job(V.n), shipped_target, S.done(V.n))

    def write(state, event):
        folded_target.add(S.done(event.bindings["n"]))
        return state

    folded_bridge = stream.fold(
        write, space=source.space_name, pattern=S.job(V.n)
    )

    # EVALUATE, a reaction's step: run an operation under the bindings. The
    # shipped form declares (on ...) and the engine folds it; this one folds
    # the same evaluation from outside.
    metta.declare_reaction(
        source.space_name, "(job $n)", "(insert &ev-reacted (shipped $n))"
    )
    reacted = metta.space("&ev-reacted")

    def evaluate(state, event):
        reacted.add(S.folded(metta.run(f"!(+ {event.bindings['n']} 0)")[0][0]))
        return state

    folded_reaction = stream.fold(
        evaluate, space=source.space_name, pattern=S.job(V.n)
    )

    try:
        source.add(S.job(1), S.job(2))

        # DELIVER: the same events, in the same order.
        assert [event.atom for event in shipped_seen] == [S.job(1), S.job(2)]
        assert [event.atom for event in folded_deliver.take()] == [
            S.job(1), S.job(2),
        ]
        # take() resets the fold, so the next read starts again.
        assert folded_deliver.take() == []

        # WRITE: the same atoms in both targets.
        assert sorted(str(atom) for atom in shipped_target.atoms()) == sorted(
            str(atom) for atom in folded_target.atoms()
        )
        assert sorted(str(atom) for atom in folded_target.atoms()) == [
            "(done 1)", "(done 2)",
        ]

        # EVALUATE: the same conclusions, one pair per write.
        assert sorted(str(atom) for atom in reacted.atoms()) == [
            "(folded 1)", "(folded 2)", "(shipped 1)", "(shipped 2)",
        ]
    finally:
        folded_reaction.cancel()
        folded_bridge.cancel()
        folded_deliver.cancel()
        shipped_bridge.cancel()
        shipped_subscription.cancel()


def test_a_fold_waits_for_an_arrival_without_polling(metta):
    """wait() is the blocking read the queueing model is written over.

    Something that arrived before the call is answered rather than waited
    for, and a deadline with nothing arriving answers the initial state
    instead of hanging.
    """
    space = metta.new_space()
    counted = metta.events().fold(
        lambda total, _event: total + 1,
        space=space.space_name,
        pattern=S.tick(V.n),
        state=0,
    )
    try:
        space.add(S.tick(1))
        assert counted.wait(timeout=2.0) == 1
        assert counted.wait(timeout=0.05) == 0
    finally:
        counted.cancel()


def test_a_fold_that_writes_into_its_own_pattern_says_so(metta):
    """A fold feeding itself cannot keep both answers, so it refuses.

    The nested step finishes first and its state would be erased by the
    outer one. Silently losing an event is what the error replaces.
    """
    space = metta.new_space()

    def feed(held, event):
        if event.atom == S.loop(1):
            space.add(S.loop(2))
        return [*held, event.atom]

    fold = metta.events().fold(
        feed, space=space.space_name, pattern=S.loop(V.n), state=[]
    )
    try:
        with pytest.raises(PettaError, match="wrote an atom its own pattern"):
            space.add(S.loop(1))
    finally:
        fold.cancel()
