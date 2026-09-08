"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/17-nars_derivation_control.metta in Python: the priority queue under the reasoner.

A sentence is `(Sentence <term-and-truth> <stamp>)`, ordinary data, so every
argument here is a built atom. `BestCandidate` takes a ranking function by
NAME, which is why `S.PriorityRank` is a symbol rather than a Python callable:
passing the ranking in is what makes one fold serve both directions.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, lib

#: Two sentences the queue claims are about, and the belief the loop derives
#: against.
QUIET = S.Sentence(S.a(S.stv(1.0, 0.5)), (1,))
LOUD = S.Sentence(S.b(S.stv(1.0, 0.9)), (2,))
PREMISE = S.Sentence(Expression((S["-->"](S.a, S.b), S.stv(1.0, 0.9))), (1,))
BELIEF = S.Sentence(Expression((S["-->"](S.b, S.c), S.stv(1.0, 0.9))), (2,))
DERIVED = S.Sentence(Expression((S["-->"](S.a, S.c), S.stv(1.0, 0.81))), (1, 2))


def twin(m):
    """Configuration, stamps, rankings, the bounded queue and the loop."""
    m += lib.nars
    f = m.fn

    # The three configuration numbers are nullary EQUATIONS rather than
    # constants in the loop, so a program can define its own budget.
    assert f["NARS.Config.MaxSteps"]() == [100]
    assert f["NARS.Config.TaskQueueSize"]() == [10]
    assert f["NARS.Config.BeliefQueueSize"]() == [100]

    # The rule that stops evidence being counted twice.
    disjoint = f["StampDisjoint"]
    assert disjoint((1, 2), (3, 4)) == [True]
    assert disjoint((1, 2), (2, 3)) == [False]
    assert disjoint((), ()) == [True]
    assert disjoint((1,), ()) == [True]

    # A merge that is sorted and order-independent; an empty addition is the
    # identity and does NOT sort what it was given.
    concat = f["StampConcat"]
    assert concat((3, 1), (2,)) == [(1, 2, 3)]
    assert concat((3, 1), ()) == [(3, 1)]
    assert concat((1,), (2,)) == concat((2,), (1,))

    # Two clauses each: a sentence answers its confidence, and the empty
    # tuple answers a sentinel far below anything real.
    assert f["PriorityRank"](LOUD) == [0.9]
    assert f["PriorityRank"](()) == [-99999.0]
    assert f["PriorityRankNeg"](LOUD) == [-0.9]
    assert f["PriorityRankNeg"](()) == [-99999.0]
    assert f["ConfidenceRank"]((S.stv(1.0, 0.9), (1,))) == [0.9]
    assert f["ConfidenceRank"](()) == [0]

    # The queue itself: a ranking function, a running best, and the tuple.
    best = f["BestCandidate"]
    assert best(S.PriorityRank, (), (QUIET, LOUD)) == [LOUD]
    assert best(S.PriorityRankNeg, (), (QUIET, LOUD)) == [QUIET]
    assert best(S.PriorityRank, (), ()) == [()]

    # The bound on that queue. Its test is `(< (length $L) $size)`, so what it
    # leaves is size MINUS ONE items, which is the arbiter's own arithmetic.
    limit = f["LimitSize"]
    assert limit((QUIET,), 5) == [(QUIET,)]
    assert limit((QUIET, LOUD), 2) == [(LOUD,)]
    assert limit((QUIET, LOUD), 1) == [()]

    # And what it keeps is the HIGHEST priority, because it drops by the
    # negated rank: bounding the queue is forgetting the least confident.
    middle = S.Sentence(S.c(S.stv(1.0, 0.5)), (3,))
    faint = S.Sentence(S.a(S.stv(1.0, 0.1)), (1,))
    assert limit((faint, LOUD, middle), 3) == [(LOUD, middle)]

    # The loop those five build. Two premises and two steps are enough:
    # a --> b and b --> c deduce a --> c, whose stamp carries both IDs.
    derived = f["NARS.Derive"]((PREMISE,), (BELIEF,), 2)
    assert DERIVED in derived[0][1]

    # A step budget of zero derives nothing, so the belief queue comes back
    # as it went in: the loop is bounded by a NUMBER, not by a fixed point.
    assert f["NARS.Derive"]((PREMISE,), (BELIEF,), 0)[0][1] == (BELIEF,)

    # And an empty task queue stops it whatever the budget is.
    assert f["NARS.Derive"]((), (BELIEF,), 100) == [((), (BELIEF,))]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 240221 inferences, 1.0106x the example's 237692; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 240221 to 239806 (-415), metta_substitute_self/3
#: probes the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 239806 to 238029 (-1777), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 238029 to 239180 (+1151), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 239180 to 239566 (+386), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
BUDGET = 239566
