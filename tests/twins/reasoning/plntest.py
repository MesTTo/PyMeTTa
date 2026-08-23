"""Purpose: examples/reasoning/plntest.metta in Python: one PLN deduction, checked.

Two syllogistic premises go in, one conclusion comes out, and the truth value
on it is computed by the PLN deduction formula with its consistency
preconditions. The claim is that conclusion.

`clamp` is the one definition whose whole body has a compiled spelling, so it
is an ordinary Python function and `min`/`max` are Python's own builtins, which
the subset lowers to the engine's. Everything else stays at the container door,
and each has its own reason:

- the two probability bounds DIVIDE, and `/` in a compiled body lowers to
  `(/ (* 1.0 $left) $right)` so an exact integer quotient stays a float the way
  Python's `/` does. The example writes MeTTa's own `/`, which that coercion is
  not, so a compiled equation would no longer be the example's;
- `conditional-probability-consistency` and `Truth_Deduction` use MeTTa's
  `and`, a generate-and-test over two values, where Python's `and`
  short-circuits on truthiness;
- `Truth_Deduction` and `|-` destructure in the HEAD, and a compiled head
  pattern must be a literal;
- `SyllogisticRuleGuard` and `STV` have literal SYMBOL heads, and a stacked
  clause's default must be a literal too, so `def g(_t=1)` writes
  `(= (g 1) ...)` but nothing writes `(= (g Inheritance) ...)`.

Each is a residue entry against P14.4. Where an operator does build the term it
is used; where it cannot, the head is named. `Truth_Deduction` carries a
genuine underscore, so it takes the bracket: the factory attribute door maps
every underscore to a hyphen, and `S.Truth_Deduction` would be a DIFFERENT
head from the example's.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, Expression, S, V, arrow, equation, fn, if_, typed

#: The deduction formula's own head, and the comparison this file needs with a
#: GROUND left operand.
#:
#: Known issue: `<` is the one comparison that builds no term at all now that
#: appendix stamp 6 gave `Atom.__lt__` to the engine's sort order, and the
#: three that do build still have no right-hand method, so a ground LEFT
#: operand reflects into the mirrored head. `(< 0 $As)` should read
#: `LESS(0, V.As)` only for the mirroring, and `V.a < 10` should build.
DEDUCTION = S["Truth_Deduction"]
LESS = fn["<"]

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Build the deduction formula, then run one syllogism through it."""
    smallest = S["smallest-intersection-probability"]
    largest = S["largest-intersection-probability"]
    consistent = S["conditional-probability-consistency"]

    @m.define
    def clamp(v, low, high):
        """Keep v inside [low, high]."""
        return min(high, max(v, low))

    m += typed(smallest, arrow(int, int, int))
    m += equation(smallest(V.As, V.Bs)).to(
        S.clamp((V.As + V.Bs - 1) / V.As, 0, 1)
    )

    m += typed(largest, arrow(int, int, int))
    m += equation(largest(V.As, V.Bs)).to(S.clamp(V.Bs / V.As, 0, 1))

    # A conditional probability is consistent when it sits between the two
    # bounds its marginals allow.
    m += typed(consistent, arrow(int, int, int, bool))
    m += equation(consistent(V.As, V.Bs, V.ABs)).to(
        LESS(0, V.As)
        & ((smallest(V.As, V.Bs) <= V.ABs) & (V.ABs <= largest(V.As, V.Bs)))
    )

    # The deduction formula itself: strength from the two conditionals, and
    # confidence as the weakest link. Preconditions unmet answer (stv 1 0).
    m += equation(DEDUCTION(S.stv(V.Ps, V.Pc), S.stv(V.Qs, V.Qc),
                            S.stv(V.Rs, V.Rc), S.stv(V.PQs, V.PQc),
                            S.stv(V.QRs, V.QRc))).to(
        if_(consistent(V.Ps, V.Qs, V.PQs) & consistent(V.Qs, V.Rs, V.QRs),
            S.stv(if_(LESS(0.9999, V.Qs),  # Qs tending to 1 would divide by zero
                      V.Rs,
                      V.PQs * V.QRs
                      + (1 - V.PQs) * (V.Rs - V.Qs * V.QRs) / (1 - V.Qs)),
                  fn.min(V.Pc, fn.min(V.Qc, fn.min(V.Rc, fn.min(V.PQc, V.QRc))))),
            S.stv(1, 0))
    )

    for link in (S.Inheritance, S.Implication):
        m += equation(S.SyllogisticRuleGuard(link)).to(TRUE)
    for concept in (S.a, S.b, S.c):
        m += equation(S.STV(concept)).to(S.stv(0.4, 0.9))

    # The syllogism: two links sharing a middle term compose into one.
    m += equation(S["|-"](((V.LinkType, V.A, V.B), V.T1),
                          ((V.LinkType, V.B, V.C), V.T2))).to(
        if_(S.SyllogisticRuleGuard(V.LinkType),
            ((V.LinkType, V.A, V.C),
             DEDUCTION(S.STV(V.A), S.STV(V.B), S.STV(V.C), V.T1, V.T2)),
            fn.empty())
    )

    assert m.fn["|-"]((S.Inheritance(S.a, S.b), S.stv(0.9, 0.9)),
                      (S.Inheritance(S.b, S.c), S.stv(0.8, 0.9))) == [
        Expression((S.Inheritance(S.a, S.c), S.stv(0.7333333333333334, 0.9)))
    ]
