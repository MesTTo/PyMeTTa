"""Purpose: exercise the thread-library example through Python-built work.

The twin covers every concurrency claim in examples/libraries/thread_lib.metta.
Assumes:
  - lib_thread publishes futures as space names accepted by await, get-atoms,
    settled?, and cancel [source: lib/lib_thread.metta:spawn; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - twin asserts all twenty-seven source claims across parallel collections,
    races, futures, timers, channels, pools, locks, and time bounds
    [measured: twin completed; command=bindings/python/tools/twin_coverage.py --measure examples/libraries/thread_lib.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Owns resources:
  - every future and timer is awaited or cancelled; the process-scoped pool
    and channel are released when the isolated twin process exits
    [measured: twin completed; command=bindings/python/tools/twin_coverage.py --measure examples/libraries/thread_lib.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V, equation

#: Successful costs from two complete concurrent ten-round observations and
#: eight subsequent complete gate-protocol observations. One original attempt
#: failed in the example before producing a twin cost and is not counted
#: [measured: 3796865..5045134 over 27 observations and 1 example failure; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 3796865,
    "maximum": 5045134,
    "observations": 27,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Run parallel collections, futures, timers, channels, pools, and locks."""
    m.eval(
        S["import!"](
            S["&self"],  # rung: import!'s target is a named space argument; handles do not yet encode there
            S.library(S.lib_thread),
        )
    )

    @m.define
    def inc(x):
        return x + 1

    @m.define(name="big?")
    def big(x):
        return x > 2

    spin = S.spin
    m.add(
        equation(spin(V.n)).to(
            S["if"](V.n > 0, spin(V.n - 1), S.done)  # rung: lowercase `done` is data in a stored equation and cannot be returned by a compiled body yet
        ),
        equation(S.slow(V.x)).to(S.let(V._, spin(300000), V.x)),  # rung: discarding a call before returning has no compiled statement spelling yet
    )

    par_map = m.fn("par-map")
    par_filter = m.fn("par-filter")
    par_forall = m.fn("par-forall")
    par_any = m.fn("par-any")
    par_race = m.fn("par-race")

    assert tuple(par_map(S.inc, (1, 2, 3, 4))) == (2, 3, 4, 5)
    assert tuple(par_map(S.inc, ())) == ()
    assert tuple(par_filter(S["big?"], (1, 2, 3, 4, 5))) == (3, 4, 5)
    assert par_forall(S["big?"], (3, 4, 5)) is True
    assert par_forall(S["big?"], (1, 4, 5)) is False
    assert par_any(S["big?"], (1, 2, 9)) is True
    assert par_any(S["big?"], (1, 2)) is False

    assert par_race((S.slow(1), S.inc(41))) == 42
    assert par_race((S.superpose(()), S.inc(41))) == 42

    spawn = m.fn("spawn")
    await_ = m.fn("await")

    future = spawn(S.inc(41))
    assert await_(future) == 42

    first, second = spawn(S.slow(1)), spawn(S.slow(2))
    assert await_(first) + await_(second) == 3

    future = spawn(S.inc(1))
    await_(future)
    assert await_(future) == 2

    assert await_.all(spawn(S.superpose((1, 2, 3)))) == [1, 2, 3]
    assert await_.all(spawn(S.superpose(()))) == []

    space_future = spawn(S.inc(1))
    assert m.fn("is-space")(space_future) is True
    await_(space_future)

    future = spawn(S.inc(41))
    await_(future)
    assert m.fn("get-atoms").all(future) == [42]

    after = m.fn("after")
    cancel = m.fn("cancel")
    settled = m.fn("settled?")

    assert await_.all(after(0.05, S.inc(41))) == [42]

    timer = after(30, S.inc(41))
    was_settled = settled(timer)
    cancel(timer)
    assert was_settled is False

    timer = after(0.05, S.inc(41))
    cancel(timer)
    m.fn("sleep")(0.25)
    assert m.fn("get-atoms").all(timer) == []

    channel = m.fn("channel")
    send = m.fn("send")
    receive = m.fn("recv")

    mailbox = channel()
    send(mailbox, S.hello)
    assert receive(mailbox) == S.hello

    mailbox = channel()
    send(mailbox, S.one)
    assert m.fn("channel-size")(mailbox) == 1

    m.fn("pool")(S.demo_pool, 2)
    submitted = m.fn("submit")(S.demo_pool, S.inc(9))
    assert await_(submitted) == 10

    here = S["&self"]  # rung: await-atom and spawned add-atom take their space as a term argument; handles do not yet encode there
    writer = spawn(S["add-atom"](here, S.ready(S.now)))  # rung: the write is data handed to a spawned engine thread, not a Python-side store mutation
    seen = m.fn("await-atom")(here, S.ready(V.what), 10)
    await_(writer)
    assert seen == S.ready(S.now)

    values = S.superpose((1, 2, 3))
    assert m.fn("with-lock").all(S.demo_lock, values) == [1, 2, 3]
    assert m.fn("with_mutex").all(S.demo_lock, values) == [1]
    assert m.fn("timeout").all(10, values) == [1, 2, 3]
    assert m.fn("timeout")(10, S.inc(41)) == 42
