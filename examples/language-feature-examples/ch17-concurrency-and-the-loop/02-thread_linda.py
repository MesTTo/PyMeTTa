"""Purpose: examples/ch17-concurrency-and-the-loop/02-thread_linda.metta in Python: the two blocking binds.

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
waited for, and a deadline that expires RAISES rather than answering nothing,
which is the absence law and Python's own way of saying a wait gave up. Both
load lib_thread in the caller's context, so `&jobs` still holds nothing but
this example's jobs and the emptiness claims stand. `await-atom` is the older
name for `peek-atom` and has no verb of its own, so the sugar claim names it
at the function namespace.

The miss is caught as `TimeoutError`, which is what these two doors raise;
`metta.Timeout`, the guide's taught spelling and what `Channel.recv` raises, is
a SUBCLASS of it, so this line keeps working when the two doors agree. The
split is a library defect the report carries, not something a twin should
paper over.

Everything else is Python: each space is created by ATOM because a space name
is a symbol, writing is `+=`, enumerating is `list`, the example's `let` chains
are assignments, the writer thread is `spawn`, taking the number out of a
`(job N)` atom is `atom[1]`, and adding two of those numbers reads their
carried scalars, since `+` over grounded atoms stages a term instead of
computing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import S, V, fn, lib, spawn


def twin(m):
    """Peek twice, take once, drain a queue, and rendezvous with a thread."""
    m += lib.thread

    @m.define
    def inc(x):
        # (= (inc $x) (+ $x 1))
        return fn.add(x, 1)

    # A peek leaves the atom, so two peeks answer the same job.
    jobs = metta.space(S.jobs)
    jobs += S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)

    # await-atom is the older name for the same thing and stays as sugar.
    assert m.fn.await_atom(jobs, S.job(V.n)) == [S.job(7)]

    # A take removes the one it answers, so the second finds nothing and gives
    # up on its deadline instead of answering the same job twice.
    assert jobs.take(S.job(V.n)) == S.job(7)
    try:
        jobs.take(S.job(V.n), deadline=0.05)
    except TimeoutError:
        gave_up = True
    else:
        gave_up = False
    assert gave_up
    assert list(jobs) == []

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    work = metta.space(S.work)
    work += S.job(1)
    work += S.job(2)
    first = work.take(S.job(V.a), deadline=1)
    second = work.take(S.job(V.b), deadline=1)
    assert first[1].value + second[1].value == 3
    assert list(work) == []

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    inbox = metta.space(S.inbox)
    writer = spawn(
        S.add_atom(inbox, S.msg(S.hello))
    )  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    seen = inbox.take(S.msg(V.what), deadline=10)
    writer.wait()
    assert seen == S.msg(S.hello)
    assert list(inbox) == []


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 14 inferences over the concurrent lane's own observations, because
#: the rendezvous waits on another thread
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 135764 to 136197, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 136197 to 136183, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 136183 to 136133, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-ENVELOPED 2026-09-01 on the operator-protocol tree. Generic Python
#: operators now dispatch through live protocols and relational twins name
#: engine heads explicitly, so ten fresh full-lane observations replace the
#: prior implementation's modes [measured: exact extrema over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: The confirming differential supplied an eleventh observation inside those
#: bounds [measured: eleventh full-lane observation 401241; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: A second ten-round observe pass stayed inside the first pass's bounds
#: [measured: exact extrema over 10 further observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: Four confirming differentials stayed inside those bounds [measured: four
#: further full-lane observations, the last 401241; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
BUDGET = {
    "minimum": 401238,
    "maximum": 401241,
    "observations": 25,
    "protocol": "full-lane/219/workers=32",
}
