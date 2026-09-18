"""Purpose: reference_loading.metta in Python with the same admission policy.

The load pragma belongs to the receiver. A lazy call compiles its body and
a background call waits for the defining home.
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/13-reference_loading.metta; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
"""

from metta import MettaError, S

MAPS = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/maps"]
BACKGROUND = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/background"]
EFFECTFUL = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/effectful"]


def twin(m):
    """Call deferred homes and refuse the initializer under both policies."""
    m.fn["pragma!"](S.load, S.lazy)
    m.from_(MAPS, S.prefix(S["lazy."]))
    assert m.fn["lazy.map-value"](41) == [42]
    assert m.fn["lazy.map-label"]() == [S.label]
    m.fn["pragma!"](S.load, S.background)
    m.from_(BACKGROUND)
    assert m.fn.background_value(41) == [42]
    for policy in (S.background, S.lazy):
        m.fn["pragma!"](S.load, policy)
        refused = False
        try:
            m.from_(EFFECTFUL)
        except MettaError as error:
            refused = True
            assert "println!" in str(error)
            assert "eager" in str(error)
        assert refused
    m.fn["pragma!"](S.load, S.eager)


#: Background loading joins a worker. Its counter includes work whose timing
#: depends on the complete lane, so this declaration records that protocol's
#: observed extrema. The ten samples were 332588, 329737, 332267, 330250,
#: 332432, 332041, 330564, 330886, 332217 and 330653, with no missing costs.
#: [measured 2026-09-10: 329737..332588 inferences over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/280/workers=32; commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
#: RE-OBSERVED 2026-09-18 under 'full-lane/293/workers=32', 329737..332588 over
#: 10 under 'full-lane/280/workers=32' to 370077..373706 over 10: the branch's
#: tip f06186a96 after the landings the point re-pin names (the compiled call
#: law, the one codec at the grounded call, the runnable cache's dependency
#: index written by the producer, the host patches of 09-17, the class units)
#: and a corpus of 293 twinned examples under the lane's 32-worker pool, so the
#: scheduler this counter answers to is a new one and the observations are this
#: tree's own rather than pooled with the earlier protocol's [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10, wt-battery-6 ai-tmp/ai-observe-f06186a96.log; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: POOLED 2026-09-18: the lane's own reading on the same tree, 369745, sits
#: under the ten rounds' floor of 370077 by 332, so it joins them under the
#: same protocol, 369745..373706 over 11, as the 2026-09-08 entry pools two
#: runs [measured 2026-09-18: python extensions/python/tools/twin_coverage.py,
#: wt-battery-4 ai-tmp/ai-twins-lane-residuals.log; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 369745..373706 over
#: 11 under 'full-lane/293/workers=32' to 369880..373517 over 10: the corpus
#: grew from 293 to 294 twinned examples when 08-guarded_rules joined it
#: (49478d67a), and a full-lane protocol names the corpus width because the
#: scheduler this counter answers to is the whole corpus under the lane's
#: 32-worker pool, so the observations are this tree's own rather than pooled
#: with the earlier protocol's [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, wt-battery-5
#: ai-tmp/ai-observe-558f40c9c.log; commit=WORKTREE].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 369880..373517 over
#: 10 under 'full-lane/294/workers=32' to 369880..373517 over 23: every full-
#: lane run under one protocol is an observation, so the envelope pools the two
#: ten-round observations on this tree with the three full-lane runs that
#: measured it (the K5 tip's lane, the assembled tree before its envelopes and
#: after), the union of the extrema over the sum of the counts, as the
#: 2026-09-08 entry pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins three times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log; commit=WORKTREE].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 369880..373517 over
#: 23 under 'full-lane/294/workers=32' to 369880..373736 over 24: every full-
#: lane run under one protocol is an observation, so the envelope pools the two
#: ten-round observations on this tree with the four full-lane runs that
#: measured it (the K5 tip's lane, the assembled tree before its envelopes,
#: after them, and after the first pooling), the union of the extrema over the
#: sum of the counts, as the 2026-09-08 entry pools two runs [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 twice and GATE_ONLY=1 sh check.sh twins four times, ai-
#: observe-558f40c9c.log, ai-observe-c6448858b.log, ai-twins-K5.log, ai-
#: twins-K6-interim.log, ai-twins-K6-final.log, ai-twins-K6-final-2.log;
#: commit=WORKTREE].
BUDGET = {
    "minimum": 369880,
    "maximum": 373736,
    "observations": 24,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
