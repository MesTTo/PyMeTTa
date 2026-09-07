"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/19-pln_derivation_control.metta in Python: the same five ideas, written a second time inside lib_pln.

NARS's queue and PLN's are separate definitions of the same shape, over each
library's own tuple helpers, so this twin is `17-nars_derivation_control.py`
with lib_pln imported and `PLN.` in place of `NARS.`: importing both would put
two definitions of every one of these names in one space.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, lib

QUIET = S.Sentence(S.a(S.stv(1.0, 0.5)), (1,))
LOUD = S.Sentence(S.b(S.stv(1.0, 0.9)), (2,))
RULE = S.Sentence(Expression((S.Implication(S.a, S.b), S.stv(1.0, 0.9))), (1,))
FACT = S.Sentence(S.a(S.stv(1.0, 0.9)), (2,))
DERIVED = S.Sentence(S.b(S.stv(1.0, 0.81)), (1, 2))


def twin(m):
    """Configuration, stamps, rankings, the bounded queue, and the loop."""
    m += lib.pln
    f = m.fn

    assert f["PLN.Config.MaxSteps"]() == [100]
    assert f["PLN.Config.TaskQueueSize"]() == [10]
    assert f["PLN.Config.BeliefQueueSize"]() == [100]

    disjoint = f["StampDisjoint"]
    assert disjoint((1, 2), (3, 4)) == [True]
    assert disjoint((1, 2), (2, 3)) == [False]
    assert disjoint((), (1,)) == [True]

    # Merged through `InsertionSort`, so the result is sorted and
    # order-independent; an empty addition leaves the stamp as it was.
    concat = f["StampConcat"]
    assert concat((3, 1), (2,)) == [(1, 2, 3)]
    assert concat((3, 1), ()) == [(3, 1)]
    assert concat((1,), (2,)) == concat((2,), (1,))

    assert f["PriorityRank"](LOUD) == [0.9]
    assert f["PriorityRank"](()) == [-99999.0]
    assert f["PriorityRankNeg"](LOUD) == [-0.9]
    assert f["PriorityRankNeg"](()) == [-99999.0]
    assert f["ConfidenceRank"]((S.stv(1.0, 0.9), (1,))) == [0.9]
    assert f["ConfidenceRank"](()) == [0]

    best = f["BestCandidate"]
    assert best(S.PriorityRank, (), (QUIET, LOUD)) == [LOUD]
    assert best(S.PriorityRankNeg, (), (QUIET, LOUD)) == [QUIET]
    assert best(S.PriorityRank, (), ()) == [()]

    # Its test is `(< (TupleCount $L) $size)`, so it leaves size MINUS ONE
    # items, and what survives is the highest-ranked.
    limit = f["LimitSize"]
    assert limit((QUIET,), 5) == [(QUIET,)]
    assert limit((QUIET, LOUD), 2) == [(LOUD,)]
    assert limit((QUIET, LOUD), 1) == [()]

    # The loop: one implication and one fact give modus ponens, with the two
    # confidences multiplied and both evidence IDs carried.
    derive = f["PLN.Derive"]
    assert derive((RULE,), (FACT,), 2)[0][1] == (FACT, DERIVED)

    # A step budget of zero derives nothing, so both queues come back as they
    # went in.
    assert derive((RULE,), (FACT,), 0) == [((RULE,), (FACT,))]

    # And an empty task queue stops it whatever the budget is.
    assert derive((), (FACT,), 100) == [((), (FACT,))]

    # `PLN.Query` is that loop with the answers filtered to one term and
    # ranked by confidence.
    assert f["PLN.Query"]((RULE, FACT), S.b, 2) == [(S.stv(1.0, 0.81), (1, 2))]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 339381 inferences, 1.0113x the example's 335573; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 339381
