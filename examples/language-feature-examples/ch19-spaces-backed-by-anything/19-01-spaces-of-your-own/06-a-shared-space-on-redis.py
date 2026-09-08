"""Purpose: examples/ch19-spaces-backed-by-anything/19-01-spaces-of-your-own/06-a-shared-space-on-redis.metta in Python: a space whose atoms live in Redis.

Once attached, `&shared` is a space HANDLE like any other, so the writes are
`space += atom`, the reads are `space[pattern]` and nothing above the seam
knows there is a network under it. That is the whole point of the foreign
seam, and it is what makes this twin read like the spaces twins.

Two things can be absent and they are asked about separately, exactly as the
original asks: the provider, which a platform without library(redis) refuses
by that capability's name, and the server, which refuses a connection.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, MeTTa, S, V, lib
from metta.errors import MettaError

ADDRESS = G("127.0.0.1:6379")


def attached(space, address):
    """Whether a Redis attach succeeded, without letting the refusal escape."""
    try:
        list(space.metta.self.fn["redis-attach"](space, address))
    except MettaError:
        return False
    return True


def available(m):
    """Whether this box has library(redis) and a server answering ADDRESS.

    The lane asks this before `twin(m)` and compares the budget below only
    where it answers True: the budget was measured against a running server,
    and without one the twin takes the same guarded path its example takes,
    whose count says nothing about it. The probe runs in an engine of its
    own, so nothing it imports or attaches moves the count `twin(m)` spends
    in the engine it is handed.
    """
    del m
    engine = MeTTa()
    try:
        home = engine.self
        try:
            home += lib.redis
        except MettaError:
            return False
        return attached(engine.space(S.probe), ADDRESS)
    finally:
        engine.close()


def twin(m):
    """Attach, write, join, remove, detach, and leave the store as found."""
    try:
        m += lib.redis
    except MettaError:
        return  # no provider: the platform has no library(redis)

    shared = m.metta.space(S.shared)
    if not attached(shared, ADDRESS):
        # The example prints its skip here. A twin has no door for prose.
        return

    detach = m.fn["redis-detach"]

    # A write goes to Redis and a read comes back from it, through the seam.
    shared += [
        S.city(S.paris, S.france),
        S.city(S.lyon, S.france),
        S.city(S.berlin, S.germany),
    ]
    assert sorted((row.c for row in shared[S.city(V.c, S.france)]), key=str) == [
        S.lyon,
        S.paris,
    ]

    # A join mixes shared facts with native ones: the engine splits the
    # conjunction per conjunct and unifies its own side.
    local = m.metta.space(S.local)
    local += S.capital(S.france, S.paris)
    assert [
        row.city
        for row in local[S.capital(V.country, V.city)]
        if shared[S.city(row.city, row.country)]
    ] == [S.paris]

    # `remove-atom` is exact and reaches the shared set, so what one process
    # takes out is gone for every other one.
    shared -= S.city(S.berlin, S.germany)
    assert shared[S.city(V.c, S.germany)] == []

    # `redis-detach` releases the binding and LEAVES the facts in Redis,
    # which is the difference from clearing a space: the next attach under
    # the same name finds them.
    detach(shared).one()
    assert attached(shared, ADDRESS)
    assert sorted((row.c for row in shared[S.city(V.c, S.france)]), key=str) == [
        S.lyon,
        S.paris,
    ]

    # And the name is owned while it is attached, so a second attach without
    # the detach is refused rather than raced.
    assert not attached(shared, ADDRESS)

    # Leaving the store as it was found, because a shared space outlives the
    # process that wrote it.
    shared -= S.city(S.paris, S.france)
    shared -= S.city(S.lyon, S.france)
    assert shared[V.any] == []
    detach(shared).one()


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 113469 inferences, 0.9558x the example's 118714; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 113476 to 46265 (-67211), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 113476 to 49056 (-64420), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 49056 to 49911 (+855), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
BUDGET = 49911
#: The count VARIES by a few tens, because every read and write crosses a
#: socket and the subscription thread's own work lands in the same counter.
#: Three single-round measurements on this branch gave 113484, 113469 and
#: 113484, a spread of 15, so the band is the midpoint plus a round 200
#: either side rather than the tree's deterministic 4
#: [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1, three times, against a redis:7.2.3-alpine container;
#: commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
ALLOWANCE = 200
