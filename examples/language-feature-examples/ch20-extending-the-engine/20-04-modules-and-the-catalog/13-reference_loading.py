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
#: --rounds 10, wt-battery-6 ai-tmp/ai-observe-f06186a96.log; commit=WORKTREE].
#: POOLED 2026-09-18: the lane's own reading on the same tree, 369745, sits
#: under the ten rounds' floor of 370077 by 332, so it joins them under the
#: same protocol, 369745..373706 over 11, as the 2026-09-08 entry pools two
#: runs [measured 2026-09-18: python extensions/python/tools/twin_coverage.py,
#: wt-battery-4 ai-tmp/ai-twins-lane-residuals.log; commit=WORKTREE].
BUDGET = {
    "minimum": 369745,
    "maximum": 373706,
    "observations": 11,
    "protocol": "full-lane/293/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
