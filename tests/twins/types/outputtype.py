"""Purpose: examples/types/outputtype.metta in Python: the output type decides.

One body, `x + 42`, three declarations, three answers. `Any` is `%Undefined%`
and lets the sum run, so `f` answers 44. `Atom` on the OUTPUT stops the result
being evaluated, so `g` answers the term `(+ 2 42)`. `Atom` on the input as
well stops the argument evaluating too, so `h` answers `(+ (+ 1 1) 42)`.

All three are ordinary annotated functions: `@m.define` publishes the arrow the
annotations name before it stores the equation, so the output type governs that
equation as soon as it lands, and calling one IS evaluating it.
"""

from typing import Any

from metta import Atom, S

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8527 to 8581, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8581 to 8592, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8592 to 8524, on the release tree:
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
#: RE-PINNED 2026-08-25, 8524 to 8534, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 8534 to 10078 (+1544), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 10078


def twin(m):
    """One body, three signatures, three answers."""

    @m.define
    def f(x: int) -> Any:
        """(: f (-> Number %Undefined%)), (= (f $x) (+ $x 42))."""
        return x + 42

    @m.define
    def g(x: int) -> Atom:
        """(: g (-> Number Atom)), the same body under a lazy OUTPUT."""
        return x + 42

    @m.define
    def h(x: Atom) -> Atom:
        """(: h (-> Atom Atom)), lazy on both sides."""
        return x + 42

    # !(test (f (+ 1 1)) 44)
    assert f(S.add(1, 1)) == [44]
    # !(test (g (+ 1 1)) (noeval (+ 2 42)))
    assert g(S.add(1, 1)) == [S.add(2, 42)]
    # !(test (h (+ 1 1)) (noeval (+ (+ 1 1) 42)))
    assert h(S.add(1, 1)) == [S.add(S.add(1, 1), 42)]
