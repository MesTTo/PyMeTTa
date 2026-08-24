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

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


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
