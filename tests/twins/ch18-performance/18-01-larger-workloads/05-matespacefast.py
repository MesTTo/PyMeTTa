"""Purpose: examples/ch18-performance/18-01-larger-workloads/05-matespacefast.metta in Python: a million and a half atoms.

`rewriteK` writes three atoms per level and recurses down two branches, so
nineteen levels leave 1,572,862 atoms in the space; `mate-space-demo` runs that
and then matches everything back out. The claim is how many came back.

The recursive equation compiles and then cannot run, which is why it is built
here. A compiled `if` wraps its condition in `py-truthy` and `==` lowers to
`py-eq`, so every level spends reductions the original does not, and the evaluator's
default 100,000 stack bound is reached long before nineteen levels: the
compiled pair answers `(Error (rewriteK (M (W ...)) 2) StackOverflow)` at K=14
where the built pair completes K=19 [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
`m.limits` bounds inferences and time and not stack depth, and the example
states no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone. Residue P14.4 and P14.14.

The count IS Python's, and it is the most expensive line in this folder.
`len(answers)` is what `(length (collapse X))` dissolves into, and here the
answers are 1,572,862 atoms: 295,442,370 inferences, 66 seconds and 5.3 GB of
resident memory in one process, against the engine's own count which never
materialises one [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. It no longer FAILS,
which it did when this twin was first written: the answer view streams where
the old door built one Prolog list, so the wall moved from "cannot run" to
"expensive". The missing door is the one peanofast.py names, a query that
projects or aggregates before it crosses (residue, P14.7); the cost of not
having it is the library's.

The space every equation writes into and matches is the HANDLE, because a space
is an ordinary term operand.
"""

from metta import S, V, equation, fn, if_, match


def twin(m):
    """Rewrite nineteen levels deep, then count what landed."""
    m += equation(S.rewriteK(V.t, V.n)).to(
        if_(V.n.eq(0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V["_1"], S.add_atom(m, S.num(S.M(V.t)))),  # rung: as above
                           (V["_2"], S.add_atom(m, S.num(S.W(V.t)))),  # rung: as above
                           (V["_3"], S.add_atom(m, S.num(S.C(V.t))))),  # rung: as above
                          (S.rewriteK(S.M(V.t), V.n - 1),
                           S.rewriteK(S.W(V.t), V.n - 1)))))

    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _rewritten = fn.rewriteK(S.Z, k)
        return match(space, S.num(V.stored), S.num(V.stored))

    assert len(m.fn.mate_space_demo(19)) == 1572862


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 68713127 to 68713120, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 68713120 to 68713144, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 68713144 to 68713105, on the release tree:
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
#: RE-PINNED 2026-08-25, 68713105 to 68713114, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 68713114 to 324566150 (+255853036): 6917bef7 made encoded
#: generator tuple yields cross as relational candidate rows the engine
#: unifies per row, where they had been direct emissions; this twin's
#: move generators pay it on every yielded move. Measured at the exact
#: pair: 32,666,762 at a58e3d17 and 116,491,178 at 6917bef7. The answers
#: are unchanged; ai-brief-p14-relational-ops-fastpath carries the
#: ground-direction fast path [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 324566150 to 324566172 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 324566172 to 74483636 (-250082536, -77.1%), the
#: largest of the family because it is the answer-heaviest: `len(...)` on an
#: effect-bearing goal had to encode and cross all 1,572,862 answers to reach
#: one number. The count and the values now come from ONE evaluation that
#: holds its answers unencoded in the engine. Crossing an answer costs
#: 9.1 + 8.0 per term node in engine inferences, measured over a depth sweep,
#: and that whole product is what a discarded length used to pay
#: [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-relational-fastpath off 694c12f7 with engine/reader.so and the MORK artefact; commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
BUDGET = 74483636
