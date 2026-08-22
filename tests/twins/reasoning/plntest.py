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
is used; where it cannot, the tuple is. `0 < V.As` would answer `(> $As 0)`
because Python reflects `<` into `>`, so `(< 0 $As)` is written the way MeTTa
writes it, as `(LT, 0, V.As)`.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, Expression, S, V, equation

#: Why this file sits below the top rung: every definition but `clamp` is at
#: the container door, for the four reasons the docstring lists, so the MeTTa
#: heads inside those equation bodies are deliberate.
RUNG = "every definition but clamp divides, uses MeTTa's and, destructures in the head, or has a symbol head, and none of those compiles"

#: The comparison head this file needs with a GROUND left operand, which is the
#: one shape Python's own operators cannot build: `<` reflects into `>`.
LT = S["<"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 33388 to 32531, -857 (-2.57%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`, which
#: is all that could move; the deduction formula is the example. `clamp` was
#: already compiled at the previous pin, so `@m.define`'s per-name admission
#: (~1.6k inferences paid once at decoration) is inside both figures. Against
#: the example's 52673 the ratio is 0.6176 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/reasoning/plntest.metta`]. Prior:
#: RE-PINNED at 33388, +1629, when `clamp` gained the decorator; ADDED
#: 2026-08-22 at 31759 by the wave-3 twin baseline.
BUDGET = 32531


def twin(m):
    """Build the deduction formula, then run one syllogism through it."""
    @m.define
    def clamp(v, low, high):
        """Keep v inside [low, high]."""
        return min(high, max(v, low))

    m += S[":"](S["smallest-intersection-probability"],
                S["->"](S.Number, S.Number, S.Number))
    m += equation(S["smallest-intersection-probability"](V.As, V.Bs)).to(
        S.clamp((V.As + V.Bs - 1) / V.As, 0, 1)
    )

    m += S[":"](S["largest-intersection-probability"],
                S["->"](S.Number, S.Number, S.Number))
    m += equation(S["largest-intersection-probability"](V.As, V.Bs)).to(
        S.clamp(V.Bs / V.As, 0, 1)
    )

    # A conditional probability is consistent when it sits between the two
    # bounds its marginals allow.
    m += S[":"](S["conditional-probability-consistency"],
                S["->"](S.Number, S.Number, S.Number, S.Bool))
    m += equation(S["conditional-probability-consistency"](V.As, V.Bs, V.ABs)).to(
        (LT, 0, V.As)
        & ((S["smallest-intersection-probability"](V.As, V.Bs) <= V.ABs)
           & (V.ABs <= S["largest-intersection-probability"](V.As, V.Bs)))
    )

    # The deduction formula itself: strength from the two conditionals, and
    # confidence as the weakest link. Preconditions unmet answer (stv 1 0).
    m += equation(S.Truth_Deduction(S.stv(V.Ps, V.Pc), S.stv(V.Qs, V.Qc),
                                    S.stv(V.Rs, V.Rc), S.stv(V.PQs, V.PQc),
                                    S.stv(V.QRs, V.QRc))).to(
        S["if"](S["conditional-probability-consistency"](V.Ps, V.Qs, V.PQs)
                & S["conditional-probability-consistency"](V.Qs, V.Rs, V.QRs),
                S.stv(S["if"]((LT, 0.9999, V.Qs),  # Qs tending to 1 would divide by zero
                              V.Rs,
                              V.PQs * V.QRs
                              + (1 - V.PQs) * (V.Rs - V.Qs * V.QRs) / (1 - V.Qs)),
                      S.min(V.Pc, S.min(V.Qc, S.min(V.Rc, S.min(V.PQc, V.QRc))))),
                S.stv(1, 0))
    )

    for link in (S.Inheritance, S.Implication):
        m += equation(S.SyllogisticRuleGuard(link)).to(TRUE)
    for concept in (S.a, S.b, S.c):
        m += equation(S.STV(concept)).to(S.stv(0.4, 0.9))

    # The syllogism: two links sharing a middle term compose into one.
    m += equation(S["|-"](((V.LinkType, V.A, V.B), V.T1),
                          ((V.LinkType, V.B, V.C), V.T2))).to(
        S["if"](S.SyllogisticRuleGuard(V.LinkType),
                ((V.LinkType, V.A, V.C),
                 S.Truth_Deduction(S.STV(V.A), S.STV(V.B), S.STV(V.C), V.T1, V.T2)),
                S.empty())
    )

    assert m.eval(S["|-"]((S.Inheritance(S.a, S.b), S.stv(0.9, 0.9)),
                          (S.Inheritance(S.b, S.c), S.stv(0.8, 0.9)))) == [
        Expression((S.Inheritance(S.a, S.c), S.stv(0.7333333333333334, 0.9)))
    ]
