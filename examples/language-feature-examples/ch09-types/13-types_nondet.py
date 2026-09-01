"""Purpose: examples/ch09-types/13-types_nondet.metta in Python: one name, two signatures.

`f` is declared for Type1 AND for Type2, so its argument arrives as either and
the OUTPUT type decides which calls survive. `T3in` is a Type1, and a Type1
argument cannot reach a Type2 answer, so `(f T3in)` has no answer at all until
`T3in` is also declared a Type2, at which point the Tdefault branch is
acceptable and answers.

The two arrows are written as the atoms they are, because one Python signature
cannot say two, and the def itself carries no annotations, so it publishes no
third arrow of its own. Its body is Python's own `if` chain, which lowers to
the example's nested conditional exactly; the comparison is `=alpha` and not
`==` for this file's own reason: `(== T2in T1in)` compares two KNOWN and
different types, which `==` refuses by name. Both references refuse the `==`
spelling too, hyperon and the mechanised interpreter alike.
"""

from metta import S, arrow, typed


def twin(m):
    """Declare two arrows for one name, then watch the output type filter."""
    # (: f (-> Type1 Type1)) (: f (-> Type2 Type2))
    m += typed(S.f, arrow(S.Type1, S.Type1))
    m += typed(S.f, arrow(S.Type2, S.Type2))

    @m.define
    def f(a):
        """(= (f $a) (if (=alpha $a T1in) T1out (if (=alpha $a T2in) T2out Tdefault)))."""
        if alpha(a, S.T1in):  # noqa: F821  -- the compiled vocabulary's own name
            return S.T1out
        if alpha(a, S.T2in):  # noqa: F821  -- the compiled vocabulary's own name
            return S.T2out
        return S.Tdefault

    # (: T1in Type1) (: T1out Type1) (: T2in Type2) (: T2out Type2)
    # (: T3in Type1) (: Tdefault Type2)
    m += [
        typed(S.T1in, S.Type1),
        typed(S.T1out, S.Type1),
        typed(S.T2in, S.Type2),
        typed(S.T2out, S.Type2),
        typed(S.T3in, S.Type1),
        typed(S.Tdefault, S.Type2),
    ]

    # !(test (f T1in) T1out)
    assert f(S.T1in) == [S.T1out]
    # !(test (f T2in) T2out)
    assert f(S.T2in) == [S.T2out]

    # (: T3in Type1) — NOTHING, because a declared result is CHECKED like
    # any argument: T3in is a Type1, so only the (-> Type1 Type1) branch
    # admits it, and that branch's own result check then rejects Tdefault,
    # which is a Type2. The (-> Type2 Type2) branch never runs because its
    # argument check refuses T3in. The .metta says this in the same words.
    # !(test (f T3in) ())
    m += typed(S.T3in, S.Type1)
    assert f(S.T3in) == []

    # Declare T3in a Type2 as well and the Type2 signature admits it.
    # (: T3in Type2)
    # !(test (f T3in) Tdefault)
    m += typed(S.T3in, S.Type2)
    assert f(S.T3in) == [S.Tdefault]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass after the conformance
#: answer updates: tools/twin_coverage.py --measure min-of-3, identical
#: across two fresh rounds on p14-integration at the store-wave merge.
#: RE-PINNED 2026-08-25, 11306 to 13718, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 13718 to 13724, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 13724 to 13689, on the release tree:
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
#: RE-PINNED 2026-08-25, 13689 to 13704, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 13704 to 13903 (+199), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 13903 to 13918 (+15), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 13918 to 9432 (-4486), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 9432 to 9441 (+9), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 9441 to 9422 (-19), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 9422
