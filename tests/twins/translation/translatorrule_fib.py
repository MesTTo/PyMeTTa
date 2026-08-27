"""examples/translation/translatorrule_fib.metta in Python: a rule that inlines a call.

`compilefib` is an ordinary definition until it is registered as a translator
rule; from then on `(compilefib 10)` is expanded and evaluated while `smartfun`
is being compiled, so the multiplication that uses it starts from 55 rather
than computing it per call.

Every one of the four is a compiled function now, including the accumulator
pair. Its MeTTa name is hyphenated and its Python name is not, which is one
declaration said once: rung 4's map turns `fib_tr` into `fib-tr` at the head
and resolves the recursive call in the body the same way. Its guard is
Python's own `==`, which the engine executes natively for wire values, so the
comparison never leaves the engine.
"""

from metta import S


def twin(m):
    """Define a tail-recursive fib, then inline one call to it at compile time."""

    @m.define
    def fib_tr(n, a, b):                  # (= (fib-tr $n $a $b)
        if n == 0:                        #    (if (== $n 0) $a
            return a                      #        (fib-tr (- $n 1) $b (+ $a $b))))
        return fib_tr(n - 1, b, a + b)

    @m.define
    def fib(n):                           # (= (fib $n) (fib-tr $n 0 1))
        return fib_tr(n, 0, 1)

    @m.define
    def compilefib(n):                    # (= (compilefib $n) (fib $n))
        return fib(n)

    # Can be left out, but then `smartfun` recomputes fib(10) on every call.
    m.fn.add_translator_rule(S.compilefib)   # (add-translator-rule! compilefib)

    @m.define
    def smartfun(b):                      # (= (smartfun $b) (* (compilefib 10) $b))
        # compilefib is a rule now, so this call is expanded and evaluated
        # while THIS definition is compiled, never per call.
        return compilefib(10) * b

    assert smartfun(42) == [2310]   # [2310]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 17717 to 17755, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 17755 to 17766, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 17766 to 17700, on the release tree:
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
#: RE-PINNED 2026-08-25, 17700 to 17710, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 17710 to 17878 (+168), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 17878 to 17898 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 17898
