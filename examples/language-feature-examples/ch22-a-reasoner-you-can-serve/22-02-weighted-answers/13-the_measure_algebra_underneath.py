"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/13-the_measure_algebra_underneath.metta in Python: the five steps the measure algebra folds.

A weighted superposition is a tuple of `(weight value)` pairs, so every
argument here is an ordinary Python tuple of atoms and every claim is one
call. `ws-sample-walk` takes the random budget EXPLICITLY, which is what
makes a sampling step testable at all.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

#: The three pairs most claims are about, and the ranked order of them.
UNRANKED = ((0.2, S.low), (0.7, S.high), (0.1, S.mid))
RANKED = ((0.7, S.high), (0.2, S.low), (0.1, S.mid))


def twin(m):
    """Rank, take, pick, walk and merge, then the surface built on them."""
    m += lib.measure
    ranked, take = m.fn["ws-ranked"], m.fn["ws-take"]
    pickmax, walk = m.fn["ws-pickmax"], m.fn["ws-sample-walk"]
    merge = m.fn["ws-merge-into"]

    # The ordering: pairs best-first, by the standard order of terms with the
    # weight written first.
    assert ranked(UNRANKED) == [RANKED]
    assert ranked(()) == [()]

    # Beam search's keep rule, total in both directions.
    assert take(RANKED, 2) == [RANKED[:2]]
    assert take(((0.7, S.high),), 5) == [((0.7, S.high),)]
    assert take(RANKED[:2], 0) == [()]
    assert take((), 2) == [()]

    # `ws-top` is those two composed.
    assert m.fn["ws-top"](UNRANKED, 2) == take(ranked(UNRANKED)[0], 2)

    # The step `ws-best` folds with: the heavier of two pairs, and the FIRST
    # of two equal ones, which is what makes the fold deterministic on ties.
    assert pickmax((0.2, S.a), (0.7, S.b)) == [(0.7, S.b)]
    assert pickmax((0.7, S.b), (0.2, S.a)) == [(0.7, S.b)]
    assert pickmax((0.5, S.a), (0.5, S.b)) == [(0.5, S.a)]

    # The inverse-transform step under `ws-sample!`, with the randomness
    # taken out: it walks the pairs subtracting weights until the budget runs
    # out.
    distribution = ((0.5, S.a), (0.3, S.b), (0.2, S.c))
    assert walk(distribution, 0.1) == [S.a]
    assert walk(distribution, 0.6) == [S.b]
    assert walk(distribution, 0.9) == [S.c]

    # The last pair absorbs everything left over, so a budget past the total
    # mass still lands on a value.
    assert walk(((0.5, S.a), (0.5, S.b)), 1.5) == [S.b]

    # The step `ws-collapse` folds with: add one pair, summing weights where
    # the VALUE already appears and appending where it does not.
    assert merge((), (0.3, S.x)) == [((0.3, S.x),)]
    assert merge(((0.3, S.x), (0.4, S.y)), (0.2, S.x)) == [((0.5, S.x), (0.4, S.y))]
    assert merge(((0.3, S.x),), (0.2, S.z)) == [((0.3, S.x), (0.2, S.z))]

    # And the fold over it is `ws-collapse`, so the surface operation is this
    # step and nothing else.
    folded = merge(merge(merge((), (0.3, S.x))[0], (0.4, S.y))[0], (0.2, S.x))
    assert m.fn["ws-collapse"](((0.3, S.x), (0.4, S.y), (0.2, S.x))) == folded


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 44683 inferences, 1.0644x the example's 41978; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 44683 to 44647 (-36), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
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
BUDGET = 44647
