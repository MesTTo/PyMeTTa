"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/04-spaces_find.metta in Python: a match used as a condition.

lib_spaces' `find` asks whether a pattern matches AND binds what it matched, so
the original nests two of them and falls back twice: no continuation gives
`MissedSecondPiece`, no starting link at all would give `MissedAllPieces`.

A call keeps both faces. Iterating `find(...)` answers what the predicate
DECIDED, one `True` per solution or a single `False` when there is none, and
`.rows` answers the bindings it made, paired position for position. So `find`
is asked here exactly as the original asks it, the decision drives Python's own
`if` the way it drives the original's, and the bindings come off the row beside
it. The library's own name reaches the bound namespace once it is imported, so
the ask is `m.fn.find(...)` and nothing is spelled twice.

The library arrives through the write door, `m += lib.spaces`, because a
library IS knowledge and the receiver is the target space. The lib
namespace joins its `lib_` family prefix with underscores kept, which is
why no bracket spelling is needed for a name MeTTa writes as
`lib_spaces`.
"""

from metta import S, V, lib


def chains(space, find):
    """Every friendship chain the space holds, with the original's fallbacks."""
    found = []
    starts = find(space, S.friend(V.a, V.b))
    for started, start in zip(starts, starts.rows, strict=True):
        if not started:
            return [S.MissedAllPieces()]
        onward = find(space, S.friend(start.b, V.c))
        for continued, row in zip(onward, onward.rows, strict=True):
            found.append(
                S.FoundChain(start.a, start.b, row.c)
                if continued
                else S.MissedSecondPiece()
            )
    return found


def twin(m):
    """Import lib_spaces, store two friendships, then walk them."""
    m += lib.spaces
    find = m.fn.find

    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # What `find` says at this door: one row per solution, bound.
    assert [(row.a, row.b) for row in find(m, S.friend(V.a, V.b)).rows] == [
        (S.a, S.b),
        (S.b, S.c),
    ]

    assert chains(m, find) == [S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 9493 to 9572, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9572 to 9573, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9573 to 9575, on the release tree:
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
#: RE-PINNED 2026-08-26, 9575 to 11401 (+1826), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 11401 to 9896 (-1505), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 9896
