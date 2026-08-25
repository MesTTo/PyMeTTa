"""Purpose: examples/spaces/matchsingle.metta in Python: two ways to take one match.

`(a b)` and `(a c)` both match, and both definitions answer only the first: one
cuts after the match, one wraps it in `once`.

Both equations are written at the container door, and one blocker is left of
the two this file used to carry. A compiled body resolves a free name against
the engine's FUNCTION REGISTRY, and neither `cut` nor `once` is in it: both are
forms the translator handles, so `is_function` answers False and a body naming
either is refused (residue, P14.4). PERFECT: `cut` and `once` join the function
registry, so a `@m.define`d body names them like any other callee
[measured 2026-08-24: `fn.once` and `fn.cut` in a compiled body are both
refused with "names no target function in this space's catalog";
commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. What is no longer a blocker is the space: a compiled `match`
takes its space through a PARAMETER, and through a handle in hand.

The facts above them are ordinary tuples, and the two calls are terms the
engine evaluates, with the handle itself in the space position.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5776 to 5814, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 5814 to 5815, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 5815 to 5821, on the release tree:
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
BUDGET = 5821


def twin(m):
    """Store two matching facts, then take one match two ways."""
    m += (S.a, S.b)
    m += (S.a, S.c)

    # (= (match-single-via-cut $space $pattern $outPattern)
    #    (let* (($x (match $space $pattern $outPattern))
    #           ($temp (cut)))
    #          $x))
    m += equation(S.match_single_via_cut(V.space, V.pattern, V.out)).to(
        S["let*"](  # rung: `cut` is a translator form, not a registry function, so no compiled body names it
            (
                (V.found, S.match(V.space, V.pattern, V.out)),  # rung: the stored body of an equation the decorator cannot compile
                (V.stop, S.cut()),
            ),
            V.found,
        )
    )

    # (= (match-single-via-once $space $pattern $outPattern)
    #    (once (match $space $pattern $outPattern)))
    m += equation(S.match_single_via_once(V.space, V.pattern, V.out)).to(
        S.once(S.match(V.space, V.pattern, V.out))  # rung: as above, with `once` in place of `cut`
    )

    # Each call carries the caller's own $x, so its answers are rows and the
    # claim reads the projection: one solution, bound to the first fact.
    assert m.fn.match_single_via_cut(m, S.a(V.x), S.a(V.x)).x == [S.b]
    assert m.fn.match_single_via_once(m, S.a(V.x), S.a(V.x)).x == [S.b]
