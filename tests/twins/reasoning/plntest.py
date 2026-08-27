"""Purpose: examples/reasoning/plntest.metta in Python: one PLN deduction, checked.

Two syllogistic premises go in, one conclusion comes out, and the truth value
on it is computed by the PLN deduction formula with its consistency
preconditions. The claim is that conclusion.

Five of the seven relations are compiled functions, so their arithmetic is
Python's own: `clamp` is `min`/`max`, the two probability bounds divide, the
consistency test is a chained comparison under `and`, and the deduction formula
destructures its five truth values with Python's `match` statement, which is
MeTTa's `case`. Their declared arrows are the signatures' annotations.

Two are `@m.rules` bundles, the door for equations whose heads are structures
or symbols rather than parameter lists: `SyllogisticRuleGuard` and `STV` fix a
SYMBOL in the head, and `|-` destructures two premise pairs in its own. A rules
body EXECUTES, so its terms are built, which is why `if_` and `S.empty()`
appear there and Python's own `if` appears in the compiled bodies.

`Truth_Deduction` carries a genuine underscore, so the head is given
explicitly: the implicit name is the mechanical image and `truth-deduction`
would be a different head from the one the example makes matchable.
"""

from metta import TRUE, Expression, S, equation, if_

#: The deduction formula's own head, and the syllogism operator, both of which
#: Python cannot spell as an identifier: one carries a genuine underscore, the
#: other is punctuation.
DEDUCTION = S["Truth_Deduction"]
ENTAILS = S["|-"]


def twin(m):
    """Build the deduction formula, then run one syllogism through it."""

    @m.define
    def clamp(value, low, high):
        """(= (clamp $v $min $max) (min $max (max $v $min)))."""
        return min(high, max(value, low))

    @m.define
    def smallest_intersection_probability(a_size: int, b_size: int) -> int:
        """(: ... (-> Number Number Number)) and (clamp (/ (- (+ $As $Bs) 1) $As) 0 1)."""
        return clamp((a_size + b_size - 1) / a_size, 0, 1)

    @m.define
    def largest_intersection_probability(a_size: int, b_size: int) -> int:
        """(: ... (-> Number Number Number)) and (clamp (/ $Bs $As) 0 1)."""
        return clamp(b_size / a_size, 0, 1)

    @m.define
    def conditional_probability_consistency(a_size: int, b_size: int, both: int) -> bool:
        """A conditional probability sits between the bounds its marginals allow."""
        # (= (conditional-probability-consistency $As $Bs $ABs)
        #    (and (< 0 $As) (and (<= (smallest ...) $ABs) (<= $ABs (largest ...)))))
        return (
            0 < a_size
            and smallest_intersection_probability(a_size, b_size)
            <= both
            <= largest_intersection_probability(a_size, b_size)
        )

    @m.define(name="Truth_Deduction")
    def truth_deduction(p, q, r, pq, qr):
        """Strength from the two conditionals, confidence as the weakest link."""
        # (= (Truth_Deduction (stv $Ps $Pc) ... ) (if (and ...) (stv ...) (stv 1 0)))
        match (p, q, r, pq, qr):
            case ((S.stv, ps, pc), (S.stv, qs, qc), (S.stv, rs, rc),
                  (S.stv, pqs, pqc), (S.stv, qrs, qrc)) if (
                    conditional_probability_consistency(ps, qs, pqs)
                    and conditional_probability_consistency(qs, rs, qrs)):
                # Qs tending to 1 would divide by zero, so that branch answers Rs.
                strength = (
                    rs
                    if 0.9999 < qs
                    else pqs * qrs + (1 - pqs) * (rs - qs * qrs) / (1 - qs)
                )
                return S.stv(strength, min(pc, min(qc, min(rc, min(pqc, qrc)))))
            case _:
                # Preconditions unmet.
                return S.stv(1, 0)

    @m.rules
    def guards():
        """The two link types the syllogism accepts, and three concept strengths."""
        # (= (SyllogisticRuleGuard Inheritance) True) and (= ... Implication) True)
        for link in (S.Inheritance, S.Implication):
            yield equation(S.SyllogisticRuleGuard(link)).to(TRUE)
        # (= (STV a) (stv 0.4 0.9)), and two more
        for name in (S.a, S.b, S.c):
            yield equation(S.STV(name)).to(S.stv(0.4, 0.9))

    @m.rules
    def syllogism(link, left, middle, right, first, second):  # noqa: PLR0917  -- a bundle's parameters ARE its equations' variables, not a call signature
        """Two links sharing a middle term compose into one."""
        # (= (|- (($LinkType $A $B) $T1) (($LinkType $B $C) $T2))
        #    (if (SyllogisticRuleGuard $LinkType)
        #        (($LinkType $A $C) (Truth_Deduction (STV $A) (STV $B) (STV $C) $T1 $T2))
        #        (empty)))
        yield equation(ENTAILS(((link, left, middle), first),
                               ((link, middle, right), second))).to(
            if_(S.SyllogisticRuleGuard(link),
                ((link, left, right),
                 DEDUCTION(S.STV(left), S.STV(middle), S.STV(right), first, second)),
                S.empty())
        )

    # !(test (|- ((Inheritance a b) (stv 0.9 0.9)) ((Inheritance b c) (stv 0.8 0.9)))
    #        ((Inheritance a c) (stv 0.7333333333333334 0.9)))
    assert m.fn["|-"]((S.Inheritance(S.a, S.b), S.stv(0.9, 0.9)),
                      (S.Inheritance(S.b, S.c), S.stv(0.8, 0.9))) == [
        Expression((S.Inheritance(S.a, S.c), S.stv(0.7333333333333334, 0.9)))
    ]


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 97580 to 97601, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 97601 to 97484, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 97484 to 97416, on the release tree:
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
#: RE-PINNED 2026-08-25, 97416 to 97394, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 97394 to 99446 (+2052), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 99446 to 99370 (-76), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 99370 to 99306 (-64), at the tabling-seam
#: merge: compiled-image layout from the library's dispatch and
#: reflection clauses, the tens-scale class this file's chain documents
#: [measured: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=tabling-seam merged tree with engine/reader.so;
#: commit=694c12f70da25a28ffe22f9209f1d75d56921f93].
#: RE-PINNED 2026-08-26, 99306 to 97839 (-1467), by the specializer
#: argument-walk fix this file's own chain named as the follow-up.
#: Planning a specialization grafts a call argument onto the equation's
#: head pattern one position at a time, and that walk metacalled a yall
#: lambda per position, so each fresh process paid '>>'/4's one-time
#: resolution wherever its first binding plan landed and 13 further
#: inferences at every later position. The walk is first-order now, at
#: 4.0 inferences per position against 17.0. [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python bindings/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
BUDGET = 97839
