"""examples/libraries/memo_stats.metta in Python: one miss, then two hits.

`sq` is an ordinary compiled definition and `memoize` is lib_memo's own
declaration, so it stays named: caching by dependency-aware invalidation is
what the library is for and Python has no word for it.

What this twin cannot show is the caching itself. A memoized function called
through `m.eval`, and therefore through every door over it, does not reach
lib_memo's dispatch hook: with the definition and the memoize both written by a
file, two calls from Python record no hit and no miss where two `!` forms in a
file record one of each. The claims here hold either way, because 81 is 81; the
divergence is in the residue table with its reproduction.
"""

from metta import S, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 27469 to 27564, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 27564 to 27585, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 27585 to 27525, on the release tree:
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
BUDGET = 27525


def twin(m):
    """Square nine three times over a memoized definition."""
    m += lib.memo

    @m.define
    def sq(x):
        return x * x

    m.eval(S.memoize(sq))

    assert sq(9) == [81]
    assert sq(9) == [81]
    assert sq(9) == [81]
