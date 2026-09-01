"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/04-plntestdirect.metta in Python: PLN deduction, driven by search.

The same deduction formula as plntest.metta beside it, but reached differently:
instead of applying a syllogistic rule to two premises, `sentence` is a
relation that either matches a stored premise or DERIVES one, and asking it for
`(Inheritance a c)` makes the search find the middle term itself.

The definitions duplicate the sibling file's because the examples do; each twin
stands alone, since the lane runs it in its own process.

Four relations are compiled functions whose control flow is Python and whose
source arithmetic and comparison relations are explicit through `fn`. Three
are `@m.rules` bundles, the door for equations whose heads are structures or
symbols. `sentence` is the interesting one: its three clauses coexist, its
recursive body is a conjunction of two sentence goals, and `(= $TV ...)` there
is a GOAL rather than a definition. `equation(lhs).to(rhs)` is the same builder
either way, because `(= lhs rhs)` in an evaluated position is an ordinary atom.

The claim is `solve`, the relational `let`: it evaluates the subject, unifies
its answer with the pattern, and hands back the subject's own variables, which
is how `$TV` leaves the search.
"""

from metta import TRUE, S, V, equation, fn

#: The deduction formula's own head, which carries a genuine underscore no
#: attribute door can spell: rung 4's map would make it `truth-deduction`.
DEDUCTION = S["Truth_Deduction"]


def twin(m):
    """Build the deduction formula, then let the search find the middle term."""

    @m.define
    def clamp(value, low, high):
        """(= (clamp $v $min $max) (min $max (max $v $min)))."""
        return fn.min(high, fn.max(value, low))

    @m.define
    def smallest_intersection_probability(a_size: int, b_size: int) -> int:
        """(: ... (-> Number Number Number)) and (clamp (/ (- (+ $As $Bs) 1) $As) 0 1)."""
        return clamp(fn.truediv(fn.sub(fn.add(a_size, b_size), 1), a_size), 0, 1)

    @m.define
    def largest_intersection_probability(a_size: int, b_size: int) -> int:
        """(: ... (-> Number Number Number)) and (clamp (/ $Bs $As) 0 1)."""
        return clamp(fn.truediv(b_size, a_size), 0, 1)

    @m.define
    def conditional_probability_consistency(a_size: int, b_size: int, both: int) -> bool:
        """A conditional probability sits between the bounds its marginals allow."""
        # (= (conditional-probability-consistency $As $Bs $ABs)
        #    (and (< 0 $As) (and (<= (smallest ...) $ABs) (<= $ABs (largest ...)))))
        return (
            fn.lt(0, a_size)
            and fn.le(smallest_intersection_probability(a_size, b_size), both)
            and fn.le(both, largest_intersection_probability(a_size, b_size))
        )

    @m.define(name="Truth_Deduction")
    def truth_deduction(p, q, r, pq, qr):
        """Strength from the two conditionals, confidence as the weakest link."""
        # (= (Truth_Deduction (stv $Ps $Pc) ... ) (if (and ...) (stv ...) (stv 1 0)))
        match (p, q, r, pq, qr):
            case (
                (S.stv, ps, pc),
                (S.stv, qs, qc),
                (S.stv, rs, rc),
                (S.stv, pqs, pqc),
                (S.stv, qrs, qrc),
            ) if conditional_probability_consistency(
                ps, qs, pqs
            ) and conditional_probability_consistency(qs, rs, qrs):
                # Qs tending to 1 would divide by zero, so that branch answers Rs.
                strength = (
                    rs
                    if fn.lt(0.9999, qs)
                    else fn.add(
                        fn.mul(pqs, qrs),
                        fn.truediv(
                            fn.mul(fn.sub(1, pqs), fn.sub(rs, fn.mul(qs, qrs))), fn.sub(1, qs)
                        ),
                    )
                )
                return S.stv(strength, fn.min(pc, fn.min(qc, fn.min(rc, fn.min(pqc, qrc)))))
            case _:
                # Preconditions unmet.
                return S.stv(1, 0)

    @m.rules
    def strengths():
        """(= (STV a) (stv 0.4 0.9)), and two more with a symbol in the head."""
        for name in (S.a, S.b, S.c):
            yield equation(S.STV(name)).to(S.stv(0.4, 0.9))

    @m.rules
    def sentences(left, middle, right, first, second, truth):  # noqa: PLR0917  -- a bundle's parameters ARE its equations' variables, not a call signature
        """Two stored premises, and one rule that derives a third."""
        # (= (sentence (Inheritance a b) (stv 0.9 0.9)) (once True))
        # (= (sentence (Inheritance b c) (stv 0.9 0.9)) (once True))
        for start, end in ((S.a, S.b), (S.b, S.c)):
            yield equation(S.sentence(S.Inheritance(start, end), S.stv(0.9, 0.9))).to(fn.once(TRUE))
        # (= (sentence (Inheritance $A $C) $TV)
        #    (once (and (and (sentence (Inheritance $A $B) $T1)
        #                    (sentence (Inheritance $B $C) $T2))
        #               (= $TV (Truth_Deduction (STV $A) (STV $B) (STV $C) $T1 $T2)))))
        yield equation(S.sentence(S.Inheritance(left, right), truth)).to(
            fn.once(
                S.sentence(S.Inheritance(left, middle), first)
                & S.sentence(S.Inheritance(middle, right), second)
                & equation(truth).to(
                    DEDUCTION(S.STV(left), S.STV(middle), S.STV(right), first, second)
                )
            )
        )

    # !(test (let $derivation (sentence (Inheritance a c) $TV) $TV)
    #        (stv 0.8166666666666668 0.9))
    derived = m.solve(V.derivation, S.sentence(S.Inheritance(S.a, S.c), V.TV))
    assert derived.TV == S.stv(0.8166666666666668, 0.9)


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 102315 to 102317, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 102317 to 102264, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 102264 to 102196, on the release tree:
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
#: RE-PINNED 2026-08-25, 102196 to 102190, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 102190 to 103927 (+1737), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 103927 to 103899 (-28), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 103899 to 103867 (-32), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 103867 to 102335 (-1532), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-09-01, 102335 to 42138 (-60197), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 42138 to 42101 (-37), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 42101 to 42383 (+282), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 42383
