"""Purpose: examples/reasoning/plntestdirect.metta in Python: PLN deduction, driven by search.

The same deduction formula as plntest.metta beside it, but reached differently:
instead of applying a syllogistic rule to two premises, `sentence` is a
relation that either matches a stored premise or DERIVES one, and asking it for
`(Inheritance a c)` makes the search find the middle term itself.

The definitions duplicate the sibling file's because the examples do; each twin
stands alone, since the lane runs it in its own process. The walls are the same
four (division, MeTTa's `and`, head destructuring, symbol heads), plus one that
belongs to this file: the recursive `sentence` clause carries `(= $TV ...)` as
a GOAL rather than as a definition, and `equation(lhs).to(rhs)` is the same
builder either way, because `(= lhs rhs)` in an evaluated position is an
ordinary atom.

The claim keeps its `let` for the reason logicprogset.py states: an evaluation
answers VALUES and `$TV` is a BINDING, so the variable leaves through the term.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V, equation

#: Why this file sits below the top rung: every definition but `clamp` is at
#: the container door, and the claim carries a binding out through a `let`.
RUNG = "every definition but clamp divides, uses MeTTa's and, destructures in the head, or has a symbol head; and the claim's $TV is a binding, which no Python door hands back"

#: The comparison head this file needs with a GROUND left operand, which is the
#: one shape Python's own operators cannot build: `<` reflects into `>`.
LT = S["<"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 34231 to 33556, -675 (-1.97%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`, which
#: is all that could move; the search is the example. `clamp` was already
#: compiled at the previous pin, so `@m.define`'s per-name admission (~1.6k
#: inferences paid once at decoration) is inside both figures. Against the
#: example's 53518 the ratio is 0.6270 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/reasoning/plntestdirect.metta`]. Prior:
#: RE-PINNED at 34231, +1629, when `clamp` gained the decorator; ADDED
#: 2026-08-22 at 32602 by the wave-3 twin baseline.
BUDGET = 33556


def twin(m):
    """Build the deduction formula, then let the search find the middle term."""
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

    m += S[":"](S["conditional-probability-consistency"],
                S["->"](S.Number, S.Number, S.Number, S.Bool))
    m += equation(S["conditional-probability-consistency"](V.As, V.Bs, V.ABs)).to(
        (LT, 0, V.As)
        & ((S["smallest-intersection-probability"](V.As, V.Bs) <= V.ABs)
           & (V.ABs <= S["largest-intersection-probability"](V.As, V.Bs)))
    )

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

    for concept in (S.a, S.b, S.c):
        m += equation(S.STV(concept)).to(S.stv(0.4, 0.9))

    # Two stored premises, and one rule that derives a third from any two that
    # share a middle term. `(= $TV ...)` here is a GOAL, not a definition.
    for left, right in ((S.a, S.b), (S.b, S.c)):
        m += equation(S.sentence(S.Inheritance(left, right), S.stv(0.9, 0.9))).to(S.once(TRUE))
    m += equation(S.sentence(S.Inheritance(V.A, V.C), V.TV)).to(
        S.once(S.sentence(S.Inheritance(V.A, V.B), V.T1)
               & S.sentence(S.Inheritance(V.B, V.C), V.T2)
               & equation(V.TV).to(S.Truth_Deduction(S.STV(V.A), S.STV(V.B), S.STV(V.C),
                                                     V.T1, V.T2)))
    )

    assert m.eval(
        S.let(V.derivation, S.sentence(S.Inheritance(S.a, S.c), V.TV), V.TV)
    ) == [S.stv(0.8166666666666668, 0.9)]
