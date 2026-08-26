"""examples/libraries/memo_spaces.metta in Python: a cache belongs to a space.

Each space compiles its own equations into its own module, so two spaces
defining the same name hold two functions, and each one caches on its own.
Sixteen claims watch that: the two answers stay apart, memoizing one leaves the
other's report false, and changing one space's equation moves only that space's
answer.

`evalc`'s Python image is the space handle itself, which is what makes this
file read: `metric.fn.shipping_cost(3)` evaluates IN &metric because the handle
carries the space, and the same call on `m` evaluates in &self. No form here
has to name a space at all, and the second space is created by ATOM,
`metta.space(S.metric)`, since a name is a symbol and never text.

The replacement equation goes to the container door. A second `@m.define` for a
name owned by a different Python function is refused with a named
`CompileError`; the write and read doors remove the old equation and put the
new one in without ceremony.
"""

import metta
from metta import S, V, equation, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 37299 to 37810, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 37810 to 37831, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 37831 to 37799, on the release tree:
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
#: RE-PINNED 2026-08-25, 37799 to 37809, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 37809 to 37274 (-535), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 37274 to 37294 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 37294
def twin(m):
    """Two spaces, one function name, two caches, and one equation change."""
    m += lib.memo

    metric = metta.space(S.metric)
    metric += equation(S.shipping_cost(V.w)).to(V.w * 9)

    @m.define
    def shipping_cost(w):
        # (= (shipping-cost $w) (* $w 2))
        return w * 2

    here, there = m.fn.shipping_cost, metric.fn.shipping_cost
    memoized, memoized_there = m.fn.is_memoized, metric.fn.is_memoized

    assert here(3) == [6]
    assert there(3) == [27]
    assert memoized(S.shipping_cost) == [False]
    assert memoized_there(S.shipping_cost) == [False]

    # Memoizing here caches this space's function and leaves the other alone.
    m.eval(S.memoize(shipping_cost))

    assert memoized(S.shipping_cost) == [True]
    assert memoized_there(S.shipping_cost) == [False]

    # Both answers stand, and stand again on the call that hits the cache.
    assert here(3) == [6]
    assert here(3) == [6]
    assert there(3) == [27]
    assert there(3) == [27]

    # Memoizing the other space's function adds a second cache, not a shared one.
    metric.eval(S.memoize(there))

    assert memoized_there(S.shipping_cost) == [True]
    assert there(3) == [27]
    assert there(3) == [27]
    assert here(3) == [6]

    # Changing one space's equation invalidates that space's cache and answers
    # the new value, while the other space keeps answering its own.
    m -= equation(S.shipping_cost(V.w)).to(V.w * 2)
    m += equation(S.shipping_cost(V.w)).to(V.w * 3)

    assert here(3) == [9]
    assert there(3) == [27]
