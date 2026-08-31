"""Purpose: the three places this library held something without a bound: a
subscription queue nobody drains, an intern cache that ages a name out by
insertion rather than by use, and load(), the one entry point most likely to
be handed code the caller did not write.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import asyncio

import pytest

from metta import S, V, aio
from metta._atom_namespace import NAMESPACE_CACHE_MAX
from metta.errors import InferenceLimitError, SubscriberError, TimeLimitError
from metta.subscribe import SUBSCRIPTION_QUEUE_MAX, Subscription


def test_the_subscription_queue_is_bounded_and_load_takes_a_budget(metta, tmp_path):
    """Three unbounded things, each measured before it was bounded.

    The queue. `Subscription._queue` was a plain list, so a no-callback
    subscription nobody drains grows for the life of the process: measured
    2000 events queued after 2000 adds, at roughly 152 bytes an Event.
    `collections.deque(maxlen=N)` is the stdlib bound and the wrong one
    here, because it discards the oldest silently. `queue.Queue` is the
    right precedent: `put_nowait` on a full queue raises `queue.Full`
    rather than dropping. So this raises, and the write it interrupts still
    stands, which makes it a SubscriberError.

    The cache. `_atom_namespace` returned on a hit before touching its
    cache, so `del cache[next(iter(cache))]` evicted by insertion age: a
    FIFO, standing beside `_atoms_core._wire_intern`, which does
    `cache.pop(name)` then `cache[name] = value`, the plain-dict spelling
    of `OrderedDict.move_to_end`, and is a correct LRU. Simulated
    2026-08-19 on a small hot set interleaved with fresh names, hit rate at
    the shipped 512: 82.4% FIFO against 88.4% LRU at 200 hot, 70.4% against
    82.4% at 400. The header promised that "repeated recent names preserve
    identity", and a FIFO does not deliver that: over 2048 touches of one
    hot name it re-minted the name FIVE times.

    load(). Nine sibling entry points took `timeout=` and `inferences=`;
    the one that runs a file the caller did not write took neither.
    """
    # ---------------------------------------------------------------- queue
    assert isinstance(SUBSCRIPTION_QUEUE_MAX, int) and SUBSCRIPTION_QUEUE_MAX > 0

    space = metta._new_space()
    try:
        queued = space.subscribe(S.ev(V.n), queue_max=3)
        try:
            for index in range(3):
                space.add(S.ev(index))
            assert len(queued.drain()) == 3

            # Draining lets it accept again: the bound is on what is held,
            # not on what has ever arrived.
            for index in range(3):
                space.add(S.ev(index))
            with pytest.raises(SubscriberError) as full:
                space.add(S.ev(99))
            assert full.value.subscription is queued
            assert "drain" in str(full.value)
            assert "3" in str(full.value)
            # The write that overflowed it still landed, and the queue kept
            # exactly its limit rather than the overflowing event.
            assert len(space.match(S.ev(V.q))) == 7
            held = queued.drain()
            assert len(held) == 3
            assert [event.atom for event in held] == [S.ev(0), S.ev(1), S.ev(2)]
        finally:
            queued.cancel()
    finally:
        space.drop()

    # ---------------------------------------------------------------- cache
    hot = S["bounds-hot"]
    for index in range(NAMESPACE_CACHE_MAX * 4):
        S[f"bounds-fresh-{index}"]
        S["bounds-hot"]
    assert S["bounds-hot"] is hot, "a name touched every round aged out anyway"

    # ---------------------------------------------------------------- load
    # The loop must not GROW: the counting spin `(spin (+ $n 1))` built 5.6GB
    # of local stack, and under gate contention the 0.05s wall alarm lost the
    # race to SWI's 7.5GB stack cap, surfacing either as a raw stack-limit
    # PrologError or, when the engine's own overflow recovery caught it, as a
    # load that RETURNED error answers instead of raising. A zero-argument
    # self-call runs flat (last-call optimized), so the alarm always gets its
    # chance, and 0.3s gives signal delivery headroom on a starved box
    # [measured 2026-08-24: the counting spin failed 2 of 6 full-battery runs
    # both ways; the flat loop raises at 0.30s exactly].
    forever = tmp_path / "forever.metta"
    forever.write_text(
        "(= (spin) (spin))\n"
        "!(with-pragma! ((max-stack-depth 300000000)) (spin))\n",
        encoding="utf-8",
    )
    with pytest.raises(InferenceLimitError):
        metta.load(forever, inferences=20_000)
    with pytest.raises(TimeLimitError):
        metta.load(forever, timeout=0.3)

    # An unbounded load still works, and still resolves an import relative
    # to the loaded file rather than the process directory.
    package = tmp_path / "package"
    package.mkdir()
    (package / "helper.metta").write_text("(= (helped) yes)\n", encoding="utf-8")
    (package / "main.metta").write_text(
        '!(import! &self "helper.metta")\n!(helped)\n', encoding="utf-8"
    )
    assert metta.load(package / "main.metta")[-1] == [S.yes]
    assert metta.load(package / "main.metta", inferences=10_000_000)[-1] == [S.yes]


def test_a_queue_bound_that_cannot_fill_is_refused(metta):
    """A bound no comparison can be true against is not a bound at all.

    Measured 2026-08-30: `queue_max=float("nan")` passed the old
    `queue_max < 1` check, because every comparison against NaN is false, and
    the step's own `len(held) >= self.queue_max` was false for exactly the
    same reason, so a subscription nobody drained held 25 of 25 events after
    25 adds and the bound above was gone. `float("inf")` did the same. The
    fix is the check the library's other counts already take, `batch`,
    `limit` and the config integers among them: the type first, so a value no
    comparison decides is refused before any comparison is made.
    """
    space = metta._new_space()
    try:
        for bound in (float("nan"), float("inf"), 3.0, "3", True):
            with pytest.raises(TypeError, match=r"queue_max must be a positive integer"):
                space.subscribe(S.ev(V.n), queue_max=bound)
        for bound in (0, -1):
            with pytest.raises(ValueError, match=r"queue_max must be positive"):
                space.subscribe(S.ev(V.n), queue_max=bound)
        # The object holds the invariant, so the class door refuses it too.
        with pytest.raises(TypeError, match=r"queue_max must be a positive integer"):
            Subscription(space.name, S.ev(V.n), None, "add", float("nan"))
        # A refused bound publishes nothing, which is only worth asserting
        # against a query that finds a real subscription on the same space.
        reflection = metta._at("&metta")
        descriptor = S.subscription(S[space.name], V.pattern, V.on)
        published = space.subscribe(S.ev(V.n), queue_max=3)
        try:
            assert len(reflection.match(descriptor)) == 1
        finally:
            published.cancel()
        with pytest.raises(TypeError):
            space.subscribe(S.ev(V.n), queue_max=float("nan"))
        assert not reflection.match(descriptor)
    finally:
        space.drop()


def test_the_async_queue_bound_is_refused_the_same_way(metta):
    """The async stream's queue takes the same bound, at the same door.

    asyncio.Queue(maxsize=float("nan")) never reports itself full, for the
    same reason the synchronous step's own comparison never fired: every
    comparison against NaN is false. The refusal belongs where the number
    arrives, which is where the stream is built rather than where it is
    first awaited.
    """
    space = metta._new_space()

    async def go():
        async with aio.AsyncMeTTa(metta=space) as am:
            for bound in (float("nan"), float("inf"), 3.0, "3", True):
                with pytest.raises(TypeError, match=r"queue_max must be a positive integer"):
                    am.watch(S.ev(V.n), queue_max=bound)
            for bound in (0, -1):
                with pytest.raises(ValueError, match=r"queue_max must be positive"):
                    am.watch(S.ev(V.n), queue_max=bound)
            # A refused bound publishes nothing, and a real one does.
            reflection = metta._at("&metta")
            descriptor = S.subscription(S[space.name], V.pattern, V.on)
            async with am.watch(S.ev(V.n), queue_max=3):
                assert len(reflection.match(descriptor)) == 1
            assert not reflection.match(descriptor)

    try:
        asyncio.run(go())
    finally:
        space.drop()
