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
#: RE-ENVELOPED 2026-09-11 under 'full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot': the lane grew from 277 to 282 twinned
#: examples (the REDS corpus example and the wave's own), and the merged tree
#: carries FROM's reference rows, BINDING's one native evaluation entry,
#: W-OBSERVE's observer guard, PERF's receipts batching and cursor retirement,
#: and the REDS shared loader; ten fresh full-lane observations read
#: 331616..335619 (spread 4003, samples [332379, 331616, 331616, 332366,
#: 333938, 333850, 335619, 332636, 332382, 334097]) where the 10 under 'full-
#: lane/280/workers=32' read 329737..332588. A run outside this envelope is a
#: real finding, and a new mode discovered later extends it with its
#: observation count rather than widening blind [measured 2026-09-11: exact
#: extrema over 10 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: POOLED 2026-09-11: a second ten-round population under the same protocol,
#: taken on the tree that carries engine/metta/limits.pl and the re-pinned
#: twins, read 331563..334090 (samples [334088, 334090, 331563, 333121,
#: 332181, 332417, 333893, 331564, 333812, 332657]); pooled with the 10 above
#: at 331616..335619, 331563..335619 over 20 observations [measured
#: 2026-09-11: exact extrema over 10 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
BUDGET = {
    "minimum": 331563,
    "maximum": 335619,
    "observations": 20,
    "protocol": "full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
