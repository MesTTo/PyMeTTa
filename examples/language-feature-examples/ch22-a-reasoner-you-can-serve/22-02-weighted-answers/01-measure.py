"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/01-measure.metta in Python: the weighted-superposition algebra.

`lib_measure` ships the algebra over `(weight value)` pairs: total, normalize,
best, top, collapse, expect, filter, flip, softmax, sample and choose. Nothing
is defined here but one helper, so every claim is a call on the imported
library through the bound function namespace, where a typo raises on the line
rather than answering nothing three calls later.

The answers are ordinary Python values once they cross: `one()` is the
cardinality door for the single answer each of these calls has, and
`ws-choose` is the one that answers nondeterministically, so it is read as the
sequence it is.
"""

from metta import S, lib


def _rows(pairs):
    """Read a weighted-pair expression as ordinary Python nested sequences."""
    return tuple(tuple(pair) for pair in pairs)


def twin(m):
    """Import the measure algebra and check its deterministic and sampled faces."""
    # !(import! &self (library lib_measure))
    m += lib.measure

    ws_total = m.fn.ws_total
    ws_normalize = m.fn.ws_normalize
    ws_best = m.fn.ws_best
    ws_top = m.fn.ws_top
    ws_collapse = m.fn.ws_collapse
    ws_expect = m.fn.ws_expect
    ws_filter = m.fn.ws_filter
    ws_flip = m.fn.ws_flip
    ws_softmax = m.fn.ws_softmax
    ws_sample = m.fn.ws_sample
    ws_choose = m.fn.ws_choose

    # The measure algebra over weighted alternatives: (weight value) pairs.
    # !(test (ws-total ((0.5 a) (0.25 b) (0.25 c))) 1.0), and seven more
    assert ws_total(((0.5, S.a), (0.25, S.b), (0.25, S.c))) == [1.0]
    assert _rows(ws_normalize(((2.0, S.a), (2.0, S.b))).one()) == (
        (0.5, S.a),
        (0.5, S.b),
    )
    assert ws_best(((0.2, S.low), (0.7, S.high), (0.1, S.mid))) == [S.high]
    assert _rows(ws_top(((0.2, S.low), (0.7, S.high), (0.1, S.mid)), 2).one()) == (
        (0.7, S.high),
        (0.2, S.low),
    )
    assert _rows(ws_collapse(((0.3, S.x), (0.4, S.y), (0.2, S.x))).one()) == (
        (0.5, S.x),
        (0.4, S.y),
    )
    assert ws_expect(((0.5, 10), (0.5, 20))) == [15.0]
    assert _rows(ws_filter(((0.9, S.keep), (0.05, S.drop)), 0.1).one()) == (
        (0.9, S.keep),
    )
    assert _rows(ws_flip(((S.cat, 0.9), (S.dog, 0.4))).one()) == (
        (0.9, S.cat),
        (0.4, S.dog),
    )

    # Softmax with temperature: cold sharpens toward the argmax, hot flattens.
    @m.define
    def first_weight(pairs):
        """(= (first-weight $ps) (index-atom (car-atom $ps) 0)), as indexing."""
        return pairs[0][0]

    # !(test (ws-best (ws-softmax ((1.0 low) (3.0 high)) 0.1)) high), and three more
    cold = ws_softmax(((1.0, S.low), (3.0, S.high)), 0.1).one()
    assert ws_best(cold) == [S.high]
    sharp = ws_softmax(((1.0, S.a), (3.0, S.b)), 0.1).one()
    assert first_weight(sharp).one() > 0.0
    flat = ws_softmax(((1.0, S.a), (3.0, S.b)), 1000.0).one()
    assert abs(first_weight(flat).one() - 0.5) < 0.01
    spread = ws_softmax(((2.0, S.a), (5.0, S.b), (1.0, S.c)), 0.7).one()
    assert abs(ws_total(spread).one() - 1.0) < 1.0e-9

    # Sampling draws only values the superposition carries, every time.
    # !(test (is-member (ws-sample! ((0.5 heads) (0.5 tails))) (heads tails)) true)
    # ... and two more
    assert ws_sample(((0.5, S.heads), (0.5, S.tails))).one() in (S.heads, S.tails)
    assert ws_sample(((1.0, S.sure),)) == [S.sure]
    assert ws_sample(((0.1, S.a), (0.2, S.b), (0.7, S.c))).one() in (S.a, S.b, S.c)

    # The nondeterministic reading: alternatives with their measure as data,
    # one answer each, which is what iterating the answers gives.
    # !(test (collapse (ws-choose ((0.6 yes) (0.4 no)))) ((0.6 yes) (0.4 no)))
    assert _rows(ws_choose(((0.6, S.yes), (0.4, S.no)))) == (
        (0.6, S.yes),
        (0.4, S.no),
    )


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 94568, maximum 94700 over
#: 28 observations under `full-lane/218/workers=32`, so the re-pin owes it an
#: envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 194271 to 194711, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 194711 to 193890, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 193890 to 193905, on the release tree:
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
#: bounds [measured: eleventh full-lane observation 87984; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: A second ten-round observe pass stayed inside the first pass's bounds
#: [measured: exact extrema over 10 further observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: Four confirming differentials stayed inside those bounds [measured: four
#: further full-lane observations, the last 87951; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-ENVELOPED 2026-09-02 after static contract discharge made retained
#: translation policy-stable. The previous bounds describe another
#: implementation, so 25 fresh full-lane observations replace them [measured:
#: minimum 88253, maximum 88352 over 25 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25;
#: fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-ENVELOPED 2026-09-02 after policy checks were confined to invalidated
#: generated contracts. Twenty-five fresh full-lane observations replace the
#: intermediate implementation's bounds [measured: minimum 88581, maximum
#: 88680 over 25 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25;
#: fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-ENVELOPED 2026-09-02 after the two generated policy-check fallbacks
#: joined the protected engine-emitted surface. Twenty-five fresh full-lane
#: observations replace the pre-protection bounds [measured: minimum 88783,
#: maximum 88882 over 25 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25;
#: fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
BUDGET = {
    "minimum": 88783,
    "maximum": 88882,
    "observations": 25,
    "protocol": "full-lane/219/workers=32",
}
