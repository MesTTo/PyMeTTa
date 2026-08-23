"""Purpose: examples/libraries/thread_lib.metta in Python: concurrency through lib_thread.

Twenty-seven claims across parallel collections, races, futures, timers,
channels, bounded pools, locks and time bounds. Every one of them is about a
lib_thread function, so every one names it through the function namespace.

Two things stay at the container door and say why on their own lines: `spin`,
whose body answers the lowercase symbol `done`, and `slow`, which discards a
call before returning.

`with_mutex` keeps the bracket at the function namespace, because that MeTTa
name really has an underscore and the attribute door maps every underscore to
a hyphen; `with-lock` beside it is the ordinary hyphenated name and takes the
attribute.

DEFECT: the rendezvous at the end ought to read
`m.fn.await_atom(m, S.ready(V.what), 10)`, the call door. Its pattern carries
`$what`, and the answer view reads every variable in a call as one of the
caller's own and answers a binding row instead of the atom that arrived, so the
claim is stated through `eval`. The space it waits on is handed over as the
HANDLE it is.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 1,248,269 inferences over the concurrent lane's own observations, because
#: the spin loop that proves a race really races is cut wherever the winning
#: branch happens to be
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Run parallel collections, futures, timers, channels, pools, and locks."""
    m.eval(S["import!"](m, S.library(S["lib_thread"])))

    @m.define
    def inc(x):
        return x + 1

    @m.define(name="big?")
    def big(x):
        return x > 2

    spin = S.spin
    m += equation(spin(V.n)).to(
        S["if"](V.n > 0, spin(V.n - 1), S.done)  # rung: lowercase `done` is data in a stored equation and cannot be returned by a compiled body yet
    )
    m += equation(S.slow(V.x)).to(S.let(V._, spin(300000), V.x))  # rung: discarding a call before returning has no compiled statement spelling yet

    par_map = m.fn.par_map
    par_filter = m.fn.par_filter
    par_forall = m.fn.par_forall
    par_any = m.fn.par_any
    par_race = m.fn.par_race

    assert par_map(S.inc, (1, 2, 3, 4)) == [Expression((2, 3, 4, 5))]
    assert par_map(S.inc, ()) == [Expression(())]
    assert par_filter(S["big?"], (1, 2, 3, 4, 5)) == [Expression((3, 4, 5))]
    assert par_forall(S["big?"], (3, 4, 5)) == [True]
    assert par_forall(S["big?"], (1, 4, 5)) == [False]
    assert par_any(S["big?"], (1, 2, 9)) == [True]
    assert par_any(S["big?"], (1, 2)) == [False]

    assert par_race((S.slow(1), S.inc(41))) == [42]
    assert par_race((S.superpose(()), S.inc(41))) == [42]

    spawn = m.fn.spawn
    await_ = m.fn["await"]

    future = spawn(S.inc(41)).one()
    assert await_(future) == [42]

    first, second = spawn(S.slow(1)).one(), spawn(S.slow(2)).one()
    assert await_(first).one() + await_(second).one() == 3

    future = spawn(S.inc(1)).one()
    await_(future).one()
    assert await_(future) == [2]

    assert list(await_(spawn(S.superpose((1, 2, 3))).one())) == [1, 2, 3]
    assert list(await_(spawn(S.superpose(())).one())) == []

    space_future = spawn(S.inc(1)).one()
    assert m.fn.is_space(space_future) == [True]
    await_(space_future).one()

    future = spawn(S.inc(41)).one()
    await_(future).one()
    assert list(m.fn.get_atoms(future)) == [42]

    after = m.fn.after
    cancel = m.fn.cancel
    settled = m.fn["settled?"]

    assert list(await_(after(0.05, S.inc(41)).one())) == [42]

    timer = after(30, S.inc(41)).one()
    was_settled = settled(timer).one()
    cancel(timer).one()
    assert was_settled is False

    timer = after(0.05, S.inc(41)).one()
    cancel(timer).one()
    m.fn.sleep(0.25).one()
    assert list(m.fn.get_atoms(timer)) == []

    channel = m.fn.channel
    send = m.fn.send
    receive = m.fn.recv

    mailbox = channel().one()
    send(mailbox, S.hello).one()
    assert receive(mailbox) == [S.hello]

    mailbox = channel().one()
    send(mailbox, S.one).one()
    assert m.fn.channel_size(mailbox) == [1]

    m.fn.pool(S.demo_pool, 2).one()
    submitted = m.fn.submit(S.demo_pool, S.inc(9)).one()
    assert await_(submitted) == [10]

    writer = m.answers(S.spawn(S["add-atom"](m, S.ready(S.now)))).one()  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    [seen] = m.eval(S["await-atom"](m, S.ready(V.what), 10))
    await_(writer).one()
    assert seen == S.ready(S.now)

    values = S.superpose((1, 2, 3))
    assert list(m.fn.with_lock(S.demo_lock, values)) == [1, 2, 3]
    assert list(m.fn["with_mutex"](S.demo_lock, values)) == [1]
    assert list(m.fn.timeout(10, values)) == [1, 2, 3]
    assert m.fn.timeout(10, S.inc(41)) == [42]
