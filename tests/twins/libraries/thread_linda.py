"""Purpose: express the thread-Linda example through Python blocking binds.

A space is a tuple space. `peek-atom` waits until a matching atom is there and
answers it LEAVING it, which is Linda's rd; `take-atom` does the same and
REMOVES exactly one, which is Linda's in. The difference is the coordination
model itself: a read is one-to-n, every consumer sees the tuple, and a take is
one-of-n, exactly one consumer gets it. Both are event-driven through the
engine's own write hooks rather than polls, and both take an optional deadline
in seconds. The non-blocking pair needs nothing new: matching is Linda's rdp
and removing is its inp.

Those four are the file's subject and they stay named, and they name their
space, because a space handle does not encode as an atom and the handle carries
no take or peek of its own; both are in the residue table. Everything else is
Python: writing is `+=`, enumerating is `list`, the example's `let` chains are
assignments, and taking the number out of a `(job N)` atom is `atom[1]`.

Assumes:
  - every engine-owned future is awaited before the isolated twin process exits
    [tested: bindings/python/tools/twin_coverage.py --measure --rounds 1
    examples/libraries/thread_linda.metta; commit=WORKTREE]
Guarantees:
  - the empirical budget applies only to the complete concurrent lane named in
    its declaration [tested:
    test_an_empirical_envelope_cannot_license_another_protocol;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V

#: Successful costs from two complete concurrent ten-round observations and
#: eight subsequent complete gate-protocol observations. One original attempt
#: failed to rendezvous and is not a cost observation
#: [measured: 154894..154908 over 27 observations and 1 twin failure; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
#: A separate ten-process serial probe observed 154894..154908; it is a
#: separate population and does not license this concurrent declaration
#: [measured: 154894..154908 over 10 observations; command=PYTHONPATH=bindings/python python -c "import sys; from pathlib import Path; sys.path.insert(0, 'bindings/python/tools'); import twin_coverage as c; e=Path('examples/libraries/thread_linda.metta').resolve(); print([c.run_twin(c.twin_for(e)).cost for _ in range(10)])"; fixture=serial fresh processes; commit=WORKTREE].
BUDGET = {
    "minimum": 154894,
    "maximum": 154908,
    "observations": 27,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Peek twice, take once, drain a queue, and rendezvous with a thread."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_thread)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def inc(x):
        return x + 1

    peek, take = m.fn("peek-atom"), m.fn("take-atom")

    # A peek leaves the atom, so two peeks answer the same job.
    jobs = m.space("&jobs")
    jobs += S.job(7)
    assert peek(S["&jobs"], S.job(V.n)) == S.job(7)  # rung: peek-atom takes its space as an ARGUMENT and the handle carries no peek of its own
    assert peek(S["&jobs"], S.job(V.n)) == S.job(7)  # rung: as above

    # await-atom is the older name for the same thing and stays as sugar.
    assert m.fn("await-atom")(S["&jobs"], S.job(V.n)) == S.job(7)  # rung: as above

    # A take removes the one it answers, so the second finds nothing and gives
    # up on its deadline instead of answering the same job twice.
    assert take(S["&jobs"], S.job(V.n)) == S.job(7)  # rung: take-atom takes its space as an ARGUMENT and the handle carries no take of its own
    assert m.eval(S["take-atom"](S["&jobs"], S.job(V.n), 0.05)) == []  # rung: as above
    assert list(jobs) == []

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    work = m.space("&work")
    work += S.job(1)
    work += S.job(2)
    first = take(S["&work"], S.job(V.a), 1)  # rung: as above
    second = take(S["&work"], S.job(V.b), 1)  # rung: as above
    assert first[1] + second[1] == 3
    assert list(work) == []

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    inbox = m.space("&inbox")
    worker = m.one(S.spawn(S["add-atom"](S["&inbox"], S.msg(S.hello))))  # rung: the spawned form is DATA handed to another thread, so its write is a term naming its space rather than a write this process performs
    seen = take(S["&inbox"], S.msg(V.what), 10)  # rung: as above
    m.eval(S["await"](worker))
    assert seen == S.msg(S.hello)
    assert list(inbox) == []
