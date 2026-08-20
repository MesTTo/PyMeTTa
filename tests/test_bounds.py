"""Purpose: the three places this library held something without a bound: a
subscription queue nobody drains, an intern cache that ages a name out by
insertion rather than by use, and load(), the one entry point most likely to
be handed code the caller did not write.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

from petta import (
    InferenceLimitError,
    S,
    SubscriberError,
    TimeLimitError,
    V,
)
from petta._atom_namespace import NAMESPACE_CACHE_MAX
from petta.subscribe import SUBSCRIPTION_QUEUE_MAX


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

    space = metta.new_space()
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
            assert len(space.query(S.ev(V.q))) == 7
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
    forever = tmp_path / "forever.metta"
    forever.write_text(
        "(= (spin $n) (spin (+ $n 1)))\n"
        "!(with-pragma! ((max-stack-depth 300000000)) (spin 0))\n",
        encoding="utf-8",
    )
    with pytest.raises(InferenceLimitError):
        metta.load(forever, inferences=20_000)
    with pytest.raises(TimeLimitError):
        metta.load(forever, timeout=0.05)

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
