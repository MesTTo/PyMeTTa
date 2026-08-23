"""Purpose: examples/types/recursive_types2.metta in Python: Peano numbers and a test.

`Nat` is `Z` or `(S n)` for a `Nat`, and `Greater` walks two of them down in
step until one runs out. The three clauses select on the SHAPE of their
arguments, `(S $x)` against `Z`, which a compiled parameter list cannot say: a
head pattern there is a literal default, a constant IN a position rather than a
structure around one. So the clauses are written as the equations they are.

The constructor pair is declared rather than written as a class for the same
kind of reason plus one more: a Python class declares ITSELF as what its
constructor returns, where `(: S (-> Nat Nat))` declares the ADT the
constructor belongs to, and the constructor here is spelled `S`, which is
already the name of the symbol factory in Python.
"""

from petta import FALSE, TRUE, S, V, arrow, equation, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Build two Peano numbers and compare them."""
    succ = S.S

    m += typed(S.Z, S.Nat)
    m += typed(succ, arrow(S.Nat, S.Nat))
    m += typed(S.Greater, arrow(S.Nat, S.Nat, bool))
    m += equation(S.Greater(succ(V.x), S.Z)).to(TRUE)
    m += equation(S.Greater(S.Z, V.x)).to(FALSE)
    m += equation(S.Greater(succ(V.x), succ(V.y))).to(S.Greater(V.x, V.y))

    one, two = succ(S.Z), succ(succ(S.Z))
    assert m.fn.Greater(one, one) == [False]
    assert m.fn.Greater(two, one) == [True]
