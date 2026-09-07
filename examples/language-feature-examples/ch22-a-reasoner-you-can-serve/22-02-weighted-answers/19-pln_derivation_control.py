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
#: RE-PINNED 2026-09-08, 339381 to 339437 (+56), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 339437 to 339075 (-362), metta_substitute_self/3
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
BUDGET = 339075
