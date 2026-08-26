"""Purpose: examples/spaces/matespace.metta in Python: a space grown to a million atoms.

`expand` doubles every `num` atom into an M-branch and a W-branch, `expandK`
does that 390 times, `mate` pairs the branches, and the whole thing answers
just over a million atoms. It is a scale example, and the scale is what its
Python twin has to respect.

The final count stays inside the engine:
`m.answers(call, under=counting).one()` maps every answer derivation to one
and crosses only the scalar 1,063,919, rather than materializing that million
atoms in Python [tested:
tools/twin_coverage.py --measure examples/spaces/matespace.metta;
commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].

The three definitions whose bodies name `case` or `once` remain terms because
neither translator form is in the function registry (residue, P14.4).
`expandK` and the driver compile: their sequencing is assignment, the driver's
ambient handle comes from `context-space`, and its seed write is `space +=`.
"""

from metta import S, V, counting, equation, fn, if_, match

#: Why this twin sits below the top rung, stated once for the whole file.
RUNG = (
    "expand, mate and add-atom-no-duplicate are built as terms: their bodies "
    "name case or once, neither of which a compiled body reaches (residue, P14.4)"
)

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 32666765 to 32666788, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 32666788 to 32666790, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 32666790 to 32666761, on the release tree:
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
#: RE-PINNED 2026-08-25, 32666761 to 32666766, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 32666766 to 32666757: the final million-answer
#: observation now uses answers(..., under=counting) and crosses one scalar
#: [measured: 32666757 inferences;
#: command=python bindings/python/tools/twin_coverage.py;
#: fixture=full-lane 390 doublings and 1063919 answers; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
#: RE-PINNED 2026-08-26, 32666757 to 116492891 (+83826134): 6917bef7 made encoded
#: generator tuple yields cross as relational candidate rows the engine
#: unifies per row, where they had been direct emissions; this twin's
#: move generators pay it on every yielded move. Measured at the exact
#: pair: 32,666,762 at a58e3d17 and 116,491,178 at 6917bef7. The answers
#: are unchanged; ai-brief-p14-relational-ops-fastpath carries the
#: ground-direction fast path [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 116492891 to 116492911 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
#: RE-PINNED 2026-08-26, 116492911 to 116491412 (-1499), by the
#: specializer argument-walk fix. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=WORKTREE].
BUDGET = 116491412
def twin(m):
    """Grow a space by 390 doublings, mate the branches, and count what is left."""
    nodup = S.add_atom_no_duplicate

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    seen = S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
    m += equation(nodup(V.space, V.atom)).to(
        if_(S.eq((), seen), S.add_atom(V.space, V.atom), S.empty())
    )

    # (= (expand) (case (match &self (num $t) $t) (($t ((add-atom-no-duplicate ...))))))
    m += equation(S.expand()).to(
        S.case(
            S.match(m, S.num(V.t), V.t),
            ((V.t, (nodup(m, S.num(S.M(V.t))), nodup(m, S.num(S.W(V.t))))),),
        )
    )

    # (= (mate) (case (match &self (num (M $t)) $t) (($t (case (once ...) ...)))))
    paired = S.case(
        S.once(S.match(m, S.num(S.W(V.t)), V.t)),
        ((V.t, nodup(m, S.num(S.C(V.t)))),),
    )
    m += equation(S.mate()).to(
        S.case(S.match(m, S.num(S.M(V.t)), V.t), ((V.t, paired),))
    )

    # (= (expandK $n) (if (== $n 0) done (let $temp1 (expand) (expandK (- $n 1)))))
    @m.define(name="expandK")  # camelCase is outside the underscore map
    def expand_k(n):
        if fn.eq(n, 0):
            return S.done
        _step = fn.expand()
        return expand_k(n - 1)

    # (= (mate-space-demo $K) (let* (($s (add-atom ...)) ($g (expandK $K)) ($h (mate)))
    #                               (match &self (num $1) (num $1))))
    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _grown = fn.expandK(k)
        _mated = fn.mate()
        return match(space, S.num(V.x), S.num(V.x))

    assert m.answers(S.mate_space_demo(390), under=counting).one() == 1063919
