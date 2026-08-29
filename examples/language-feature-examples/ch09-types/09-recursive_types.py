"""Purpose: examples/ch09-types/09-recursive_types.metta in Python: one name, two arrows.

A blacksmith turns Metal into a Sword, and also into a Paperclip. Both arrows
are declared for the one name, so every question about the name answers twice,
and an application answers the results of both. Nothing here is a function
definition: there is no equation for `blacksmith` at all, only what its type
says, which is why the declarations are written as the facts they are.

The last claim is the one worth reading twice. `(iron blacksmith)` is not an
application, it is a two-element expression, so its type is the expression of
its parts' types, elementwise, and it answers once per arrow the second element
has.
"""

from metta import S, arrow, typed


def twin(m):
    """Declare two arrows for one name, then ask four questions."""
    kind = m.fn.get_type
    sword = arrow(S.Metal, S.Sword)
    paperclip = arrow(S.Metal, S.Paperclip)

    # (: blacksmith (-> Metal Sword)) (: blacksmith (-> Metal Paperclip))
    # (: iron Metal) (: gold Metal)
    m += typed(S.blacksmith, sword)
    m += typed(S.blacksmith, paperclip)
    m += typed(S.iron, S.Metal)
    m += typed(S.gold, S.Metal)

    # !(test (get-type iron) Metal)
    assert m.type(S.iron) == S.Metal
    # !(test (collapse (get-type blacksmith))
    #        ((-> Metal Sword) (-> Metal Paperclip)))
    assert kind(S.blacksmith) == [sword, paperclip]
    # !(test (collapse (get-type (blacksmith iron))) (Sword Paperclip))
    assert kind(S.blacksmith(S.iron)) == [S.Sword, S.Paperclip]
    # !(test (collapse (get-type (iron blacksmith)))
    #        ((Metal (-> Metal Sword)) (Metal (-> Metal Paperclip))))
    assert kind(S.iron(S.blacksmith)) == [S.Metal(sword), S.Metal(paperclip)]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 2273 to 3032, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3032 to 3033, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3033 to 3041, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 3041 to 3088 (+47), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 3088
