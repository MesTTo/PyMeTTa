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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 240221
