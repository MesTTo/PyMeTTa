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

    # Shift invariance is the claim the max-subtraction inside ws-softmax
    # exists for: the same two weights come back at 1.0 and 2.0, at 1000.0
    # and 1001.0, and at -1000.0 and -999.0. Exponentiating directly gave NaN
    # at the top end and an "ws-normalize requires positive total mass"
    # refusal at the bottom, and the scores a network produces are exactly
    # the ones that reach those ends.
    # (= (both-weights $ps) ((first-weight $ps) (first-weight (cdr-atom $ps))))
    @m.define
    def both_weights(pairs):
        """The first two weights, so a shift shows as one comparison."""
        head, *rest = pairs
        return (first_weight(pairs), first_weight(rest))

    # !(test (both-weights (ws-softmax ((1.0 a) (2.0 b)) 1.0))
    #        (both-weights (ws-softmax ((1000.0 a) (1001.0 b)) 1.0))), and one more
    unshifted = both_weights(ws_softmax(((1.0, S.a), (2.0, S.b)), 1.0).one())
    assert unshifted == both_weights(
        ws_softmax(((1000.0, S.a), (1001.0, S.b)), 1.0).one()
    )
    assert unshifted == both_weights(
        ws_softmax(((-1000.0, S.a), (-999.0, S.b)), 1.0).one()
    )

    # !(test (ws-peak ((1.0 a) (7.0 b) (3.0 c))) 7.0)
    assert m.fn.ws_peak(((1.0, S.a), (7.0, S.b), (3.0, S.c))) == [7.0]

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
#: ENVELOPE 2026-09-08, 127527..127626 over 37 observations of 'full-
#: lane/231/workers=32': `ws-sample!` draws from the distribution it is given,
#: and three of the nineteen claims are about a draw, so a point pin on it is a
#: claim about a schedule and not about this twin. Spread 99 [measured
#: 2026-09-08: `python extensions/python/tools/twin_coverage.py --observe`, two
#: runs of 12 and 25 rounds pooled; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the every-atom merge widened
#: the corpus from 231 to 277 twinned examples and the scheduler this counter
#: answers to is the lane's own 32-worker pool over that corpus: 25 observations
#: pooled from two `--observe` runs of 10 and 15 rounds read 127613..127679 where the
#: 37 under 'full-lane/231/workers=32' read 127527..127626. A run outside this envelope is a
#: re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeTW-observe-10.log and -15.log; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because metta_substitute_self/3 now
#: probes a term for the text &self before walking it, where the twins-lane merge's
#: one-equation door walked every natively added equation, so this counter's whole
#: envelope moved down by the equations it adds: 25 observations pooled from two
#: `--observe` runs of 10 and 15 rounds read 127397..127496 where the 25 under
#: 'full-lane/277/workers=32' read 127613..127679. A run outside this envelope is a re-observation,
#: not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/law3-observe-10.log and -15.log; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9) and
#: every runnable form pays fewer inferences per scope, so this counter's whole
#: envelope moved down by its runnables: 25 observations pooled from two
#: `--observe` runs of 10 and 15 rounds read 125619..125718 where the 25 under
#: 'full-lane/277/workers=32' read 127397..127496. A run outside this envelope is a re-observation,
#: not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeFL-observe-10.log and -15.log; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 125673..125739
#: over 15 observations to 126937..127036 over 27: the module boundary merged
#: with trunk (refactor/engine-and-libraries-as-modules at b64291369): the
#: twin's host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine. The
#: observations are this tree's own rather than pooled with the earlier ones,
#: because pooling would mix two boot images and the spread an envelope states
#: is a claim about ONE; ten rounds, then fifteen, plus the gate's own
#: readings between them, all under the same protocol on the same tree
#: [measured 2026-09-08: python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/merged68-observe-10.log and
#: merged68-observe-15.log; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 125619..125718
#: over 25 observations to 125673..125739 over 15: boot content moved
#: with the every-closed-set-derived branch -- the refusal table and the typing
#: point are modules this package did not have, three convert doors became one,
#: per-library faces are projections, and the engine gained a catalog watch
#: point -- which shifts SWI clause-indexing shape and moves a twin count by
#: tens. The observations are this tree's own rather than pooled with the
#: earlier ones, because pooling would mix two boot images and the spread an
#: envelope states is a claim about ONE [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 15,
#: ai-tmp/ai-derive-observe.log; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-OBSERVED 2026-09-08 after typed host doors joined the boot catalog.
#: Ten complete rounds observed 125695..125794. Sampling still selects
#: different alternatives; catalog lookup now includes the declared doors.
#: These observations replace the earlier catalog's envelope
#: [measured: exact extrema over 10 successful observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 130379..130488 (spread 109) over 24 observations,
#: replacing the earlier envelope of the tree before this one. Its count is the
#: scheduler's, three of its claims are about a sampled draw, so the envelope
#: is exact extrema and a run outside it is a re-observation under --observe,
#: not a re-pin [measured 2026-09-09: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, twice,
#: beside the plain lane runs ai-tmp records; fixture=full-lane/277/workers=32;
#: commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: POOLED 2026-09-09: published 130379..130488 over 24
#: observations, receipt pass 130422..130488 over 10, and
#: final pass 130378..130706 over 10. Exact extrema and counts
#: retain the existing empirical protocol; no point budget becomes an envelope.
#: [measured: two complete ten-round passes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: RE-OBSERVED 2026-09-10 after setting the file-search cache lifetime
#: before engine creation. This complete ten-round population uses
#: 130411..130477 over 10 observations. Earlier protocol
#: samples remain above as history and do not enter this envelope.
#: [measured: all 277 pairs, this twin succeeds in every round; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: POOLED 2026-09-10: the earlier before-boot population has 130411..130477
#: over ten samples; the receipt-frame repair's complete population has
#: 130378..130477 over ten. The full lanes at 17bec75f1 and e70deddaa add
#: 130444 and 130477. Their exact pooled extrema are 130378..130477 over 22
#: observations under the same cache-normalised protocol. Earlier runtime
#: samples remain identified separately; the receipt watcher now transfers
#: ownership at live completion. No point becomes an envelope. The final gate
#: is an independent validation sample [measured 2026-09-10: two complete ten-
#: round populations and two full lane checks; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: the retained 22 observations have 130378..130477. The
#: full lane at 71535ae17 adds 130411; a further complete ten-round population
#: at db8640733 adds 130378..130477. All 2770 new samples succeed. Exact pooled
#: extrema are 130378..130477 over 33 observations under the same before-boot
#: cache protocol. No point becomes an envelope [measured 2026-09-10: three
#: complete ten-round populations and three full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: retain the previous33 observations and both full-gate
#: samples (3fb950149: 130411; 503e21f8a: 130444), then append the complete
#: ten-round populations (2f1be07e9: 130411..130477; e93f2028d:
#: 130411..130477). Both populations have2770 successful samples, no failures
#: and no point movements or excursions. The e93f2028d population measures the
#: repaired concurrent join; the2f1be07e9 observation retains its own version.
#: Exact pooled extrema are130378..130477 over55 samples, without padding. No
#: point becomes an envelope. [measured 2026-09-10: five complete ten-round
#: populations and five full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-11: keep all 55 previous observations, append the two
#: complete gate readings (895878bbe=130444, 4d4fa2c55=130444), then all ten
#: qualified 4d4fa2c55 rounds (130411..130477). The resulting 67 observations
#: have exact extrema 130378..130477. The prior scheduling mechanisms remain;
#: this complete lane also measures the explicit pending-definition provider.
#: No targeted or instrumented reading enters an envelope. The end-of-wave
#: battery re-observes and re-pins the whole lane on the merged tree under this
#: protocol, pooling every empirical extension with its count and mechanism.
#: [measured 2026-09-11: six complete ten-round populations and seven full-lane
#: readings; command=python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 and sh check.sh twins; fixture=full-lane/277/workers=32/file-
#: search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-ENVELOPED 2026-09-11 under 'full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot': the lane grew from 277 to 282 twinned
#: examples (the REDS corpus example and the wave's own), and the merged tree
#: carries FROM's reference rows, BINDING's one native evaluation entry,
#: W-OBSERVE's observer guard, PERF's receipts batching and cursor retirement,
#: and the REDS shared loader; ten fresh full-lane observations read
#: 131890..131989 (spread 99, samples [131989, 131890, 131956, 131956, 131989,
#: 131890, 131989, 131989, 131956, 131923]) where the 67 under 'full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot'
#: read 130378..130477. A run outside this envelope is a real finding, and a
#: new mode discovered later extends it with its observation count rather than
#: widening blind [measured 2026-09-11: exact extrema over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds
#: 10; fixture=full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: POOLED 2026-09-11: a second ten-round population under the same protocol,
#: taken on the tree that carries engine/metta/limits.pl and the re-pinned
#: twins, read 131888..131987 (samples [131888, 131954, 131987, 131987,
#: 131954, 131921, 131921, 131888, 131954, 131954]); pooled with the 10 above
#: at 131890..131989, 131888..131989 over 20 observations [measured
#: 2026-09-11: exact extrema over 10 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
#: RE-OBSERVED 2026-09-18 under 'full-lane/293/workers=32', 130378..130477 over
#: 67 under 'full-lane/277/workers=32' to 134811..134910 over 10: the branch's
#: tip f06186a96 after the landings the point re-pin names (the compiled call
#: law, the one codec at the grounded call, the runnable cache's dependency
#: index written by the producer, the host patches of 09-17, the class units)
#: and a corpus of 293 twinned examples under the lane's 32-worker pool, so the
#: scheduler this counter answers to is a new one and the observations are this
#: tree's own rather than pooled with the earlier protocol's [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10, wt-battery-6 ai-tmp/ai-observe-f06186a96.log; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 134811..134910 over
#: 10 under 'full-lane/293/workers=32' to 134844..134910 over 10: the corpus
#: grew from 293 to 294 twinned examples when 08-guarded_rules joined it
#: (49478d67a), and a full-lane protocol names the corpus width because the
#: scheduler this counter answers to is the whole corpus under the lane's
#: 32-worker pool, so the observations are this tree's own rather than pooled
#: with the earlier protocol's [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, wt-battery-5
#: ai-tmp/ai-observe-558f40c9c.log; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 134844..134910 over
#: 10 under 'full-lane/294/workers=32' to 134811..134910 over 23: every full-
#: lane run under one protocol is an observation, so the envelope pools the two
#: ten-round observations on this tree with the three full-lane runs that
#: measured it (the K5 tip's lane, the assembled tree before its envelopes and
#: after), the union of the extrema over the sum of the counts, as the
#: 2026-09-08 entry pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins three times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 134811..134910 over
#: 23 under 'full-lane/294/workers=32' to 134811..134910 over 24: every full-
#: lane run under one protocol is an observation, so the envelope pools the two
#: ten-round observations on this tree with the four full-lane runs that
#: measured it (the K5 tip's lane, the assembled tree before its envelopes,
#: after them, and after the first pooling), the union of the extrema over the
#: sum of the counts, as the 2026-09-08 entry pools two runs [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 twice and GATE_ONLY=1 sh check.sh twins four times, ai-
#: observe-558f40c9c.log, ai-observe-c6448858b.log, ai-twins-K5.log, ai-
#: twins-K6-interim.log, ai-twins-K6-final.log, ai-twins-K6-final-2.log;
#: commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 134811..134910 over
#: 24 under 'full-lane/294/workers=32' to 134811..134910 over 25: every full-
#: lane run under one protocol is an observation, so the envelope pools the two
#: ten-round observations on this tree with the five full-lane runs that
#: measured it (the K5 tip's lane, the assembled tree before its envelopes,
#: after them, after the first pooling, and the tip e28c4f2f5 beside a second
#: battery), the union of the extrema over the sum of the counts, as the
#: 2026-09-08 entry pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins five times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log, ai-twins-K6-final-2.log, ai-twins-tip-e28c4f2f5.log;
#: commit=0e767924501d8b25d1994f128d96c503d867e408].
#: RE-OBSERVED 2026-09-19 under 'full-lane/294/workers=32', 134811..134910 over
#: 25 under 'full-lane/294/workers=32' to 133662..133728 over 10: the trunk
#: merged (f97c4b0a3, petta's 61 commits since c75181adc) with the definition
#: batch's load pushed as the running load (2da1155e3): the engine moved under
#: every twin, 263 of the 276 re-pinned twins cheaper and 13 dearer (median
#: -1.25%), through the compiled runnable envelope, the trunk's trailed scopes
#: and compiled context readers, the host listener door and the receipts loop
#: probing the owner once per set, so the envelope is this tree's own
#: observation under the same 294-wide protocol [measured 2026-09-19: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, ai-
#: observe-4c0533704.log; commit=55d451b670949c2dc9d2ab7bc678f33f21094bd2].
BUDGET = {
    "minimum": 133662,
    "maximum": 133728,
    "observations": 10,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}

#: DIVERGED 2026-09-07, the example holds 2 atoms the twin does not (2 =) and
#: the twin holds 2 the example does not (1 =, 1 @doc): the twin is an ordinary
#: Python program and its body lowers to the engine's own forms: a match
#: statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: DIVERGED 2026-09-07, the example holds 2 atoms the twin does not (2 =) and
#: the twin holds 4 atoms the example does not (2 =, 2 @doc): the claims the
#: twin gained bring the definitions and the library rows they ask through, so
#: the two spaces differ by exactly those [measured 2026-09-07: the two stored-
#: atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: DIVERGED 2026-09-18, the example holds 2 atoms the twin does not (2 =) and
#: the twin holds 4 atoms the example does not (2 =, 2 @doc): a compiled body
#: spells a positional call of a bound callee as the plain application and a
#: lambda bare where it is applied (e59104ace), so the twin's stored equations
#: meet the example's spelling where they did not, and where they still differ
#: the twin stores what its own Python spelling stores [measured 2026-09-18:
#: the two stored-atom surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=bf5f100591493a91324b1d7552b5ad2731601691].
DIVERGENCE = "98e5f4b7422d1cd6d535895b94f00b154251a9e2f95db22d0b9a4d213052d7b8"
