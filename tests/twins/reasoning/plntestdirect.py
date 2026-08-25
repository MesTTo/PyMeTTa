"""Purpose: examples/reasoning/plntestdirect.metta in Python: PLN deduction, driven by search.

The same deduction formula as plntest.metta beside it, but reached differently:
instead of applying a syllogistic rule to two premises, `sentence` is a
relation that either matches a stored premise or DERIVES one, and asking it for
`(Inheritance a c)` makes the search find the middle term itself.

The definitions duplicate the sibling file's because the examples do; each twin
stands alone, since the lane runs it in its own process.

Four relations are compiled functions whose arithmetic is Python's own, and
three are `@m.rules` bundles, the door for equations whose heads are structures
or symbols. `sentence` is the interesting one: its three clauses coexist, its
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
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
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
BUDGET = 102196


def twin(m):
    """Build the deduction formula, then let the search find the middle term."""

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
            yield equation(S.sentence(S.Inheritance(start, end), S.stv(0.9, 0.9))).to(
                fn.once(TRUE)
            )
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
