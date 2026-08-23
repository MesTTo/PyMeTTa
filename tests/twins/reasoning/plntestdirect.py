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

The claim is `solve`, the relational `let`: it evaluates the subject, unifies
its answer with the pattern, and hands back the subject's own variables, which
is how `$TV` leaves the search.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V, arrow, equation, fn, if_, typed

#: The deduction formula's own head, and the two comparison heads this file
#: builds terms with. Python's `<`, `>`, `<=` and `>=` order atoms and build
#: nothing, so every comparison TERM outside a compiled body names its head.
DEDUCTION = S["Truth_Deduction"]
LESS, AT_MOST = fn["<"], fn["<="]

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Build the deduction formula, then let the search find the middle term."""
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

    m += typed(consistent, arrow(int, int, int, bool))
    m += equation(consistent(V.As, V.Bs, V.ABs)).to(
        LESS(0, V.As)
        & (AT_MOST(smallest(V.As, V.Bs), V.ABs)
           & AT_MOST(V.ABs, largest(V.As, V.Bs)))
    )

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

    for concept in (S.a, S.b, S.c):
        m += equation(S.STV(concept)).to(S.stv(0.4, 0.9))

    # Two stored premises, and one rule that derives a third from any two that
    # share a middle term. `(= $TV ...)` here is a GOAL, not a definition.
    for left, right in ((S.a, S.b), (S.b, S.c)):
        m += equation(S.sentence(S.Inheritance(left, right), S.stv(0.9, 0.9))).to(
            fn.once(TRUE)
        )
    m += equation(S.sentence(S.Inheritance(V.A, V.C), V.TV)).to(
        fn.once(S.sentence(S.Inheritance(V.A, V.B), V.T1)
                & S.sentence(S.Inheritance(V.B, V.C), V.T2)
                & equation(V.TV).to(DEDUCTION(S.STV(V.A), S.STV(V.B), S.STV(V.C),
                                              V.T1, V.T2)))
    )

    derived = m.solve(V.derivation, S.sentence(S.Inheritance(S.a, S.c), V.TV))
    assert derived.TV == S.stv(0.8166666666666668, 0.9)
