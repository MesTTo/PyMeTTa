"""Purpose: examples/libraries/thread_linda.metta in Python: the two blocking binds.

A space is a tuple space. `peek-atom` waits until a matching atom is there and
answers it LEAVING it, which is Linda's rd; `take-atom` does the same and
REMOVES exactly one, which is Linda's in. The difference is the coordination
model itself: a read is one-to-n, every consumer sees the tuple, and a take is
one-of-n, exactly one consumer gets it. Both are event-driven through the
engine's own write hooks rather than polls, and both take an optional deadline
in seconds. The non-blocking pair needs nothing new: matching is Linda's rdp
and removing is its inp.

The blocking binds are the handle verbs the coordination family rules,
`jobs.peek(S.job(V.n))` and `jobs.take(...)`: each answers the ONE atom it
waited for, and a deadline that expires raises `TimeoutError` rather than
answering nothing, which is Python's own way of saying a wait gave up. Both
load lib_thread in the caller's context, so `&jobs` still holds nothing but
this example's jobs and the emptiness claims stand. `await-atom` is the older
name for `peek-atom` and has no verb of its own, so the sugar claim names it
at the function namespace.

Everything else is Python: writing is `+=`, enumerating is `list`, the
example's `let` chains are assignments, taking the number out of a `(job N)`
atom is `atom[1]`, and adding two of those numbers reads their carried
scalars, since `+` over grounded atoms stages a term instead of computing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 14 inferences over the concurrent lane's own observations, because
#: the rendezvous waits on another thread
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Peek twice, take once, drain a queue, and rendezvous with a thread."""
    m.fn["import!"](m, S.library(S["lib_thread"]))

    @m.define
    def inc(x):
        return x + 1

    # A peek leaves the atom, so two peeks answer the same job.
    jobs = petta.space("&jobs")
    jobs += S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)

    # await-atom is the older name for the same thing and stays as sugar.
    assert m.fn.await_atom(jobs, S.job(V.n)) == [S.job(7)]

    # A take removes the one it answers, so the second finds nothing and gives
    # up on its deadline instead of answering the same job twice.
    assert jobs.take(S.job(V.n)) == S.job(7)
    gave_up = False
    try:
        jobs.take(S.job(V.n), deadline=0.05)
    except TimeoutError:
        gave_up = True
    assert gave_up
    assert list(jobs) == []

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    work = petta.space("&work")
    work += S.job(1)
    work += S.job(2)
    first = work.take(S.job(V.a), deadline=1)
    second = work.take(S.job(V.b), deadline=1)
    assert first[1].value + second[1].value == 3
    assert list(work) == []

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    inbox = petta.space("&inbox")
    worker = m.answers(S.spawn(S["add-atom"](inbox, S.msg(S.hello)))).one()  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    seen = inbox.take(S.msg(V.what), deadline=10)
    m.fn["await"](worker).one()
    assert seen == S.msg(S.hello)
    assert list(inbox) == []
