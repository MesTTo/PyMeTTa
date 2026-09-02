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
  - a fold may thread its aggregate through an engine State cell, or use a
    declared algebra merge as its entire step [tested:
    test_fold_into_state_updates_the_shared_engine_cell,
    test_fold_under_counting_and_tropical_uses_the_algebra_as_the_step;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - rejected subscription guards do not wake a blocked stream, while an
    accepted identity-preserving step does [tested:
    test_a_rejected_guard_event_does_not_end_a_blocking_stream,
    test_an_accepted_identity_step_still_wakes_its_waiter; commit=438506a1688c78a383499973b6a89fa6bb559629]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import threading
import time

import pytest

import metta as metta_module
from metta import S, State, V, counting, tropical
from metta.errors import MettaError
from metta.foreign import SpaceProvider, delivery_promise
from metta.subscribe import bridge


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
    metta._register_space(loud, "&ev-declared")
    metta._register_space(quiet, "&ev-silent")
    target = metta._new_space()
    try:
        # The promise is an ordinary declaration atom, so a MeTTa program
        # reads what the engine acts on.
        rows = metta._at("&metta").match(S.events(V.ctx, V.delivery, V.order))
        promises = {str(row.ctx): (str(row.delivery), str(row.order)) for row in rows}
        assert promises["&ev-declared"] == ("per-write-exactly", "ordered")
        assert "&ev-silent" not in promises
        assert delivery_promise(quiet) is None

        # Served: the three models, on the declared foreign space.
        seen: list = []
        subscription = metta._at("&ev-declared").subscribe(
            S.tick(V.n), seen.append
        )
        rule = bridge(
            metta._at("&ev-declared"), S.tick(V.n), target, S.heard(V.n)
        )
        metta._at("&ev-declared").reacts("(tick $n)", "(insert &ev-mirror (reacted $n))"
        )
        mirror = metta._at("&ev-mirror")
        try:
            metta._at("&ev-declared").add(S.tick(1))
            assert [event.bindings["n"] for event in seen] == [1]
            assert target.match(S.heard(V.n))
            assert mirror.match(S.reacted(V.n))
        finally:
            rule.cancel()
            subscription.cancel()

        # Refused: each of the three, naming what is missing.
        with pytest.raises(MettaError, match="declares no event capability"):
            metta._at("&ev-silent").subscribe(S.tick(V.n), seen.append)
        with pytest.raises(MettaError, match="declares no event capability"):
            bridge(metta._at("&ev-silent"), S.tick(V.n), target)
        with pytest.raises(MettaError, match="events &ev-silent"):
            metta._at("&ev-silent").reacts("(tick $n)", "(insert &ev-mirror (reacted $n))"
            )

        # The refusal is surgical: what the provider does implement still
        # works, so this is a withdrawn promise rather than a broken space.
        metta._at("&ev-silent").add(S.tick(2))
        assert S.tick(2) in quiet.stored
        assert metta._at("&ev-silent").match(S.tick(V.n))
    finally:
        metta._unregister_space("&ev-silent")
        metta._unregister_space("&ev-declared")


def test_a_native_space_needs_no_declaration_to_be_watched(metta):
    """The engine's own store is not a context making a promise.

    Every write into a native space runs seam:atom_added/2, so
    per-write-exactly and ordered are facts about this engine rather than
    assumptions about a provider, and explain says so without anything
    having been declared.
    """
    space = metta._new_space()
    seen: list = []
    subscription = space.subscribe(S.native(V.x), seen.append)
    try:
        space.add(S.native(S.one))
        assert [event.bindings["x"] for event in seen] == [S.one]
        explained = {
            str(item.head): item
            for item in metta.run(
                f"!(explain (match {space.name} (native $x) $x))"
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
    source = metta._new_space()
    shipped_target, folded_target = metta._new_space(), metta._new_space()
    shipped_seen: list = []

    # DELIVER, subscribe's step: hand the event to a callback.
    shipped_subscription = source.subscribe(S.job(V.n), shipped_seen.append)
    folded_deliver = stream.fold(
        lambda held, event: [*held, event],
        space=source.name,
        pattern=S.job(V.n),
        state=[],
    )

    # WRITE, bridge's step: land the template's instantiation elsewhere.
    shipped_bridge = bridge(source, S.job(V.n), shipped_target, S.done(V.n))

    def write(state, event):
        folded_target.add(S.done(event.bindings["n"]))
        return state

    folded_bridge = stream.fold(
        write, space=source.name, pattern=S.job(V.n)
    )

    # EVALUATE, a reaction's step: run an operation under the bindings. The
    # shipped form declares (on ...) and the engine folds it; this one folds
    # the same evaluation from outside.
    metta._at(source.name).reacts("(job $n)", "(insert &ev-reacted (shipped $n))"
    )
    reacted = metta._at("&ev-reacted")

    def evaluate(state, event):
        reacted.add(S.folded(metta.run(f"!(+ {event.bindings['n']} 0)")[0][0]))
        return state

    folded_reaction = stream.fold(
        evaluate, space=source.name, pattern=S.job(V.n)
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
    space = metta._new_space()
    counted = metta.events().fold(
        lambda total, _event: total + 1,
        space=space.name,
        pattern=S.tick(V.n),
        state=0,
    )
    try:
        space.add(S.tick(1))
        assert counted.wait(timeout=2.0) == 1
        assert counted.wait(timeout=0.05) == 0
    finally:
        counted.cancel()


def test_an_accepted_identity_step_still_wakes_its_waiter(metta):
    """An accepted event counts even when the reducer preserves its state."""
    source = metta._new_space()
    folded = metta.events().fold(
        lambda held, _event: held,
        space=source.name,
        pattern=S.p30_identity(V.n),
        state=[],
    )
    received = []

    def wait_once() -> None:
        received.append(folded.wait(timeout=10.0))

    waiters_before = folded._registry.waiters
    consumer = threading.Thread(target=wait_once)
    consumer.start()
    deadline = time.monotonic() + 5.0
    while (
        folded._registry.waiters == waiters_before
        and consumer.is_alive()
        and time.monotonic() < deadline
    ):
        time.sleep(0.001)

    try:
        assert folded._registry.waiters > waiters_before
        source.add(S.p30_identity(1))
        consumer.join(5.0)
    finally:
        folded.cancel()
        consumer.join(5.0)

    assert not consumer.is_alive()
    assert received == [[]]


def test_a_fold_that_writes_into_its_own_pattern_says_so(metta):
    """A fold feeding itself cannot keep both answers, so it refuses.

    The nested step finishes first and its state would be erased by the
    outer one. Silently losing an event is what the error replaces.
    """
    space = metta._new_space()

    def feed(held, event):
        if event.atom == S.loop(1):
            space.add(S.loop(2))
        return [*held, event.atom]

    fold = metta.events().fold(
        feed, space=space.name, pattern=S.loop(V.n), state=[]
    )
    try:
        with pytest.raises(MettaError, match="wrote an atom its own pattern"):
            space.add(S.loop(1))
    finally:
        fold.cancel()


def test_fold_into_state_updates_the_shared_engine_cell(metta):
    """The step sees the State handle and writes the process-shared cell."""
    source = metta._new_space()
    total = State(0, space=metta)

    def accumulate(cell, event):
        cell.value += int(event.n)

    folded = metta.events().fold(
        accumulate,
        space=source.name,
        pattern=S.amount(V.n),
        into=total,
    )
    try:
        source.add(S.amount(2), S.amount(5))
        assert total.value == 7
        assert folded.state is total
    finally:
        folded.cancel()


def test_fold_under_counting_and_tropical_uses_the_algebra_as_the_step(metta):
    """With no body, merge and its identity are the complete fold."""
    source = metta._new_space()
    counted = metta.events().fold(
        space=source.name,
        pattern=S.offer(V.n),
        under=counting,
    )
    with metta_module.under(counting):
        scoped_counted = metta.events().fold(
            space=source.name,
            pattern=S.offer(V.n),
        )
    cheapest = metta.events().fold(
        space=source.name,
        pattern=S.fact(V.cost, V.proposition),
        under=tropical,
    )
    try:
        source.add(S.offer(8), S.offer(5), S.offer(3))
        source.add(S.fact(8, S.route(S.a)), S.fact(3, S.route(S.b)))
        assert counted.take() == 3
        assert scoped_counted.take() == 3
        assert cheapest.take() == 3
    finally:
        cheapest.cancel()
        scoped_counted.cancel()
        counted.cancel()


def test_a_fold_binds_its_own_pattern_and_never_a_stored_event_variable(metta):
    """Delivery matches directionally, which two spellings stopped sharing.

    Event delivery binds the WATCHING pattern's variables against the atom
    that arrived; a variable stored inside that atom is data and stays
    unbound. Two branches wrote this call two ways on the same day: one kept
    the private directional matcher, the other spelled it `unify`, which was
    a synonym at that moment and became symmetric hours later when the root
    door was made symmetric in both argument orders. The merge kept the
    directional call and nothing pinned the choice, so this fixes the
    spelling to the meaning: a symmetric call here would fill the stored
    variable from the pattern and deliver an event the watcher never asked
    for.
    """
    source = metta._new_space()
    seen = []

    def collect(held, event):
        seen.append(event.bindings)
        return held

    fold = metta.events().fold(
        collect, space=source.name, pattern=S.edge(S.a, V.to), state=None
    )
    try:
        source.add(S.edge(S.a, S.b))
        source.add(S.edge(V.stored, S.b))
    finally:
        fold.cancel()

    assert seen, "the ground arrival was not delivered at all"
    assert seen[0]["to"] == S.b
    # The second atom carries a variable where the pattern has the ground
    # symbol `a`. A directional match refuses it; a symmetric one would bind
    # the STORED variable to `a` and deliver a second event.
    assert len(seen) == 1, (
        f"a stored variable was filled from the watching pattern: {seen}"
    )

def test_an_abandoned_watch_cancels_itself(scratch_space):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import gc

    from metta import S, V
    from metta import subscribe as _subscribe

    space = scratch_space
    before = len(_subscribe._subscriptions_for(space._space))
    iterator = space.watch(S.tick(V.n))
    assert len(_subscribe._subscriptions_for(space._space)) == before + 1
    del iterator
    gc.collect()
    # close() is the contract; the finalize backstop covers abandonment,
    # so a dropped iterator cannot keep a live subscription delivering
    # into nothing.
    assert len(_subscribe._subscriptions_for(space._space)) == before


def test_a_standing_query_takes_matchs_guard(metta):
    """match() has guarded since it existed; a subscription could not.

    The filtering had to live in every callback, which means every matching
    write crossed into Python to be dropped there, and a queue-mode
    subscription filled with events its consumer did not want. One guard sits
    at the single delivery point both disciplines pass through
    [measured 2026-08-31].
    """
    m = metta._at("&self")
    seen = []
    sub = m.subscribe(
        S.order(V.id, V.total), lambda e: seen.append(e.atom), where=V.total.ge(100)
    )
    try:
        for pair in ((1, 20), (2, 500), (3, 90), (4, 250)):
            m.add(S.order(*pair))
    finally:
        sub.cancel()
    assert [str(atom) for atom in seen] == ["(order 2 500)", "(order 4 250)"]

    # Queue mode passes the same point, so it drops the same events.
    queued = m.subscribe(S.ticket(V.n), where=V.n.ge(3))
    try:
        for n in (1, 5, 2, 7):
            m.add(S.ticket(n))
        assert [str(event.atom) for event in queued.drain()] == [
            "(ticket 5)",
            "(ticket 7)",
        ]
    finally:
        queued.cancel()


def test_a_rejected_guard_event_does_not_end_a_blocking_stream(metta):
    """P30: a rejected event is not an arrival for a guarded subscription.

    Start the stream after the rejected write. A false arrival counter makes
    events() read the empty queue and stop; a real wait remains blocked until
    the accepted write arrives.
    """
    source = metta._new_space()
    subscription = source.subscribe(S.p30_job(V.n), where=V.n.ge(10))
    source.add(S.p30_job(1))

    received = []
    failures: list[BaseException] = []
    finished = threading.Event()

    def consume_one() -> None:
        try:
            received.append(next(subscription.events(timeout=10.0)))
        except BaseException as error:
            failures.append(error)
        finally:
            finished.set()

    waiters_before = subscription._registry.waiters
    consumer = threading.Thread(target=consume_one)
    consumer.start()
    deadline = time.monotonic() + 5.0
    while (
        not finished.is_set()
        and subscription._registry.waiters == waiters_before
        and time.monotonic() < deadline
    ):
        time.sleep(0.001)

    try:
        assert finished.is_set() or subscription._registry.waiters > waiters_before
        source.add(S.p30_job(12))
        consumer.join(5.0)
    finally:
        subscription.cancel()
        consumer.join(5.0)

    assert not consumer.is_alive()
    assert failures == []
    assert [event.atom for event in received] == [S.p30_job(12)]


def test_why_refuses_the_question_whose_premise_is_false(metta):
    """A diagnostic that answers a false premise is worse than one that refuses.

    Space.why() and Answers.why() were two implementations of one question.
    They agreed word for word on every genuine miss and disagreed about the
    premise: asked why (job $id $pri) matched nothing, when it matches two
    atoms, one refused and the other answered "2 job atom(s) exist here but
    none unifies with it" [measured 2026-08-31]. One implementation now, so
    the guarded question is askable too, and that is the one worth asking: an
    empty query is either a pattern that found nothing or a guard that
    rejected what it found.
    """
    m = metta._at("&self")
    m.add(S.why_job(1, 2), S.why_job(2, 3))
    assert "headed by why-absent" in m.why(S.why_absent(V.x))
    with pytest.raises(ValueError, match="explains an empty query"):
        m.why(S.why_job(V.id, V.pri))
    assert "guard" in m.why(S.why_job(V.id, V.pri), where=V.pri.ge(100))
