"""Purpose: examples/libraries/thread_lib.metta in Python: concurrency through lib_thread.

Twenty-seven claims across parallel collections, races, futures, timers,
channels, bounded pools, locks and time bounds. Four of those cells have a
package function and take it, `par_map`, `race`, `spawn` and `channel`, and a
spawned future carries `wait`, `settled` and `cancel` as methods, so
`spawn(S.inc(41)).wait()` is the example's `(await (spawn ...))`.

The rest of lib_thread has no Python door yet and descends one rung to the
function namespace, which is where the ladder is visible in this file: the
`par_filter`/`par_forall`/`par_any` siblings of `par_map`, the one-shot timer
`after` and the `await`/`cancel`/`settled?` verbs its bare handle needs (the
package's timer is `every`, which repeats and is a different program), the
bounded `pool`, the two locks and lib_thread's own `timeout`. That last one is
not `m.limits(timeout=)`: the with-block bounds the engine's own call, while
`(timeout 10 X)` runs X under a wall clock and KEEPS every answer, which is
the claim beside `with_mutex` here.

All four MeTTa definitions are compiled. `spin` answers the lowercase symbol
`done`, which the `S` factory says inside a body, and `slow` discards a call
before returning, which an assignment to `_` says: both are exactly what
`(let $_ ... $x)` means.

`with_mutex` keeps the bracket at the function namespace, because that MeTTa
name really has an underscore and the attribute door maps every underscore to
a hyphen; `with-lock` beside it is the ordinary hyphenated name and takes the
attribute.

The rendezvous at the end waits with the handle's own verb, `m.peek(...)`,
Linda's rd: it answers the ONE atom it waited for rather than a binding row.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import time

from metta import Expression, S, V, channel, par_map, race, spawn

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 1,248,269 inferences over the concurrent lane's own observations, because
#: the spin loop that proves a race really races is cut wherever the winning
#: branch happens to be
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Run parallel collections, futures, timers, channels, pools, and locks."""
    m.fn["import!"](m, S.library(S["lib_thread"]))

    @m.define
    def inc(x):
        # (= (inc $x) (+ $x 1))
        return x + 1

    @m.define(name="big?")
    def big(x):
        # (= (big? $x) (> $x 2))
        return x > 2

    @m.define
    def spin(n):
        # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done))
        return spin(n - 1) if n > 0 else S.done

    @m.define
    def slow(x):
        # (= (slow $x) (let $_ (spin 300000) $x))
        _ = spin(300000)
        return x

    # par-map preserves the input list's order however the elements finish.
    assert list(par_map(S.inc, (1, 2, 3, 4))) == [2, 3, 4, 5]
    assert list(par_map(S.inc, ())) == []
    assert m.fn.par_filter(S["big?"], (1, 2, 3, 4, 5)) == [Expression((3, 4, 5))]
    assert m.fn.par_forall(S["big?"], (3, 4, 5)) == [True]
    assert m.fn.par_forall(S["big?"], (1, 4, 5)) == [False]

    # par-any stops at the first element that holds, and answers True even
    # though the elements before it fail.
    assert m.fn.par_any(S["big?"], (1, 2, 9)) == [True]
    assert m.fn.par_any(S["big?"], (1, 2)) == [False]

    # The fast branch wins and the slow one is stopped, so this returns without
    # waiting for (slow 1). A branch that fails drops out rather than ending
    # the race.
    assert race(S.slow(1), S.inc(41)) == 42
    assert race(S.superpose(()), S.inc(41)) == 42

    # A future evaluates on its own thread; wait() waits for it. Two of them
    # overlap, which is the whole point.
    assert list(spawn(S.inc(41)).wait()) == [42]

    first, second = spawn(S.slow(1)), spawn(S.slow(2))
    assert first.wait().one() + second.wait().one() == 3

    # Waiting twice answers the same thing without waiting again.
    twice = spawn(S.inc(1))
    twice.wait()
    assert list(twice.wait()) == [2]

    # A future IS a space, so it holds the expression's whole ANSWER SET rather
    # than just the first answer.
    assert list(spawn(S.superpose((1, 2, 3))).wait()) == [1, 2, 3]
    assert list(spawn(S.superpose(())).wait()) == []
    assert m.fn.is_space(spawn(S.inc(1))) == [True]

    # Being a space, it reads back with the ordinary space operations too.
    settled_future = spawn(S.inc(41))
    settled_future.wait()
    assert list(settled_future) == [42]

    # Timers are futures that start later, so (after ...) is setTimeout and
    # there is no separate clearTimeout: the same cancel that stops a spawn
    # stops a timer. A pending timer is simply not settled yet.
    after, cancel = m.fn.after, m.fn.cancel
    settled = m.fn["settled?"]
    await_ = m.fn["await"]

    assert list(await_(after(0.05, S.inc(41)))) == [42]

    timer = after(30, S.inc(41)).one()
    was_settled = settled(timer).one()
    cancel(timer).one()
    assert was_settled is False

    timer = after(0.05, S.inc(41)).one()
    cancel(timer).one()
    time.sleep(0.25)
    assert list(timer) == []

    # A channel is a mailbox. The term is copied across, so the receiver gets
    # its own copy and no binding crosses.
    mailbox = channel()
    mailbox.send(S.hello)
    assert mailbox.recv() == S.hello

    queued = channel()
    queued.send(S.one)
    assert len(queued) == 1

    # A pool bounds the fan-out; submit answers the same handle await takes.
    m.fn.pool(S.demo_pool, 2).one()
    assert await_(m.fn.submit(S.demo_pool, S.inc(9))) == [10]

    # Blocking until another thread writes the atom, event-driven through the
    # engine's own write hooks. The spawned branch does the writing.
    writer = spawn(S.add_atom(m, S.ready(S.now)))  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    seen = m.peek(S.ready(V.what), deadline=10)
    writer.wait()
    assert seen == S.ready(S.now)

    # with-lock keeps every answer. SWI's with_mutex, which the built-in form
    # uses, is once/1 and would answer (1) here. Bounding by wall clock keeps
    # them too, unlike a bare call_with_time_limit.
    values = S.superpose((1, 2, 3))
    assert list(m.fn.with_lock(S.demo_lock, values)) == [1, 2, 3]
    assert list(m.fn["with_mutex"](S.demo_lock, values)) == [1]
    assert list(m.fn.timeout(10, values)) == [1, 2, 3]
    assert m.fn.timeout(10, S.inc(41)) == [42]
