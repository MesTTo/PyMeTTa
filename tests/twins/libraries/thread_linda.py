"""Purpose: examples/libraries/thread_linda.metta in Python: the two blocking binds.

A space is a tuple space. `peek-atom` waits until a matching atom is there and
answers it LEAVING it, which is Linda's rd; `take-atom` does the same and
REMOVES exactly one, which is Linda's in. The difference is the coordination
model itself: a read is one-to-n, every consumer sees the tuple, and a take is
one-of-n, exactly one consumer gets it. Both are event-driven through the
engine's own write hooks rather than polls, and both take an optional deadline
in seconds. The non-blocking pair needs nothing new: matching is Linda's rdp
and removing is its inp.

DEFECT, twice over, and it decides how the four blocking claims are written.
They ought to read `jobs.peek((S.job, V.n))` and `jobs.take(...)`, the handle
verbs the coordination family rules. Two things stop them here. `Space.peek`
and `Space.take` import lib_thread INTO the space they are called on, so
`&jobs` would hold the library's own atoms and this example's `(get-atoms
&jobs)` claim, that the space is empty afterwards, could not be made at all.
And the pattern carries `$n`, which the answer view reads as one of the
caller's own variables, so the call door would answer a binding row where the
claim is about the atom. The space itself is handed over as the HANDLE it is,
which is what R2's term-operand encoding bought.

Everything else is Python: writing is `+=`, enumerating is `list`, the
example's `let` chains are assignments, and taking the number out of a
`(job N)` atom is `atom[1]`.
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
#: commit=WORKTREE].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
BUDGET = 1


def twin(m):
    """Peek twice, take once, drain a queue, and rendezvous with a thread."""
    m.eval(S["import!"](m, S.library(S["lib_thread"])))

    @m.define
    def inc(x):
        return x + 1

    peek, take = S["peek-atom"], S["take-atom"]

    # A peek leaves the atom, so two peeks answer the same job.
    jobs = petta.space("&jobs")
    jobs += S.job(7)
    assert m.eval(peek(jobs, S.job(V.n))) == [S.job(7)]
    assert m.eval(peek(jobs, S.job(V.n))) == [S.job(7)]

    # await-atom is the older name for the same thing and stays as sugar.
    assert m.eval(S["await-atom"](jobs, S.job(V.n))) == [S.job(7)]

    # A take removes the one it answers, so the second finds nothing and gives
    # up on its deadline instead of answering the same job twice.
    assert m.eval(take(jobs, S.job(V.n))) == [S.job(7)]
    assert m.eval(take(jobs, S.job(V.n), 0.05)) == []
    assert list(jobs) == []

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    work = petta.space("&work")
    work += S.job(1)
    work += S.job(2)
    [first] = m.eval(take(work, S.job(V.a), 1))
    [second] = m.eval(take(work, S.job(V.b), 1))
    assert first[1] + second[1] == 3
    assert list(work) == []

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    inbox = petta.space("&inbox")
    worker = m.answers(S.spawn(S["add-atom"](inbox, S.msg(S.hello)))).one()  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    [seen] = m.eval(take(inbox, S.msg(V.what), 10))
    m.eval(S["await"](worker))
    assert seen == S.msg(S.hello)
    assert list(inbox) == []
