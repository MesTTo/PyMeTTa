"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/05-spaces_succeedspredicate.metta in Python: a predicate that binds.

lib_spaces' `succeedsPredicate` takes a space, a relation and its arguments as
one tuple, and answers whether the relation holds. Ground arguments make it a
membership test, which is the first claim; variable arguments make it a
generator, and the second claim USES what it bound.

Both claims are ordinary Python calls. A call answers what the predicate
decided, and `.rows` answers the bindings it made beside those decisions, so a
question carrying the caller's own variables hands back one row per solution
and the `if` that consumes it is Python's own. The library's own name reaches
the bound namespace once it is imported, camel case and all, because the
attribute door spells a name the catalog holds exactly.

The library arrives through the write door, `m += lib.spaces`, because a
library IS knowledge and the receiver is the target space. The lib
namespace joins its `lib_` family prefix with underscores kept, which is
why no bracket spelling is needed for a name MeTTa writes as
`lib_spaces`.
"""

from metta import S, V, lib


def twin(m):
    """Ask a predicate a ground question, then a binding one."""
    m += lib.spaces
    succeeds = m.fn.succeedsPredicate

    # Nothing matches, so the ground question is False.
    assert succeeds((m, S.friend, S.tim, S.tom)).one() is False

    m += (S.friend, S.a, S.b)

    # The binding question answers what it bound, one row per solution.
    assert [(row.a, row.b) for row in succeeds((m, S.friend, V.a, V.b)).rows] == [
        (S.a, S.b)
    ]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7282 to 7337, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 7337 to 7338, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 7338 to 7340, on the release tree:
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
#: RE-PINNED 2026-08-26, 7340 to 7413 (+73), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 7413
