"""examples/basics/factorial.metta in Python: recursion through a conditional.

`@m.define` reads the function as syntax and writes the equation, so Python's
conditional expression IS MeTTa's `if` and the recursive call is the same call
the equation makes.

The source stores `==`. Python's comparison compiles to the engine-native
`py-eq` head, so the twin deliberately stores a different equation while
keeping the comparison inside the engine. The digest lane reports that
spelling difference.
"""

#: Inferences this twin spends, its own tripwire. INTERIM PIN 2026-08-24,
#: identity.py's and spaces3.py's own precedent: two lane tests fixture on
#: this file's REAL point budget, so it is priced ahead of the corpus-wide
#: pass and re-priced there with everything else. Min-of-3 on the Stage D
#: integration merge, three identical readings [measured 2026-08-24 through
#: twin_coverage --measure on the merged tree at 5e02a52d].
#: RE-PINNED 2026-08-25 at the store wave: the first-force of this
#: twin's definitions lands inside the measured block, a fixed additive
#: (min-of-3 7591, identical across two fresh rounds and the lane run).
#: RE-PINNED 2026-08-25, 7591 to 7610, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7610 to 7623, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7623 to 7555, on the release tree:
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
#: RE-PINNED 2026-08-25, 7555 to 7565, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 7565 to 7558 (-7), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=WORKTREE].
BUDGET = 7558


def twin(m):
    """Define the factorial and run it."""
    @m.define(name="facF")
    def fac_f(n):
        # Source: (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        # Twin:   (= (facF $n) (if (py-eq $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    assert fac_f(10) == [3628800]
