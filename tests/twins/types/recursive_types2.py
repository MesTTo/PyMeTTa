"""Purpose: examples/types/recursive_types2.metta in Python: Peano numbers and a test.

`Nat` is `Z` or `(S n)` for a `Nat`, and `Greater` walks two of them down in
step until one runs out. `Nat` itself is a Python class, so the three arrows
are written from Python types through the one conversion table.

The three clauses select on the SHAPE of their arguments, `(S $x)` against `Z`,
which is what `@m.rules` is for: it lands bare coexisting equations, derives no
guard, and its parameters ARE the equations' variables. A compiled parameter
list reaches none of it, because a head pattern there is a literal default, a
constant IN a position rather than a structure around one.

The constructor pair is declared rather than written as a class for one reason
beyond the head shapes: a Python class declares ITSELF as what its constructor
returns, where `(: S (-> Nat Nat))` declares the ADT the constructor belongs to
(friction, P14.10). The constructor here is also spelled `S`, which is already
the name of the symbol factory, so it is written `S.S`.
"""

from metta import FALSE, TRUE, S, arrow, equation, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
BUDGET = 1


class Nat:
    """The MeTTa type `Nat`, so the three arrows can be built from Python types."""


def twin(m):
    """Build two Peano numbers and compare them."""
    succ = S.S

    # (: Z Nat) (: S (-> Nat Nat)) (: Greater (-> Nat Nat Bool))
    m += typed(S.Z, Nat)
    m += typed(succ, arrow(Nat, Nat))
    m += typed(S.Greater, arrow(Nat, Nat, bool))

    @m.rules
    def order(smaller, larger):
        """The example's three clauses, over two shared rule variables."""
        # (= (Greater (S $x) Z) True)
        yield equation(S.Greater(succ(smaller), S.Z)).to(TRUE)
        # (= (Greater Z $x) False)
        yield equation(S.Greater(S.Z, smaller)).to(FALSE)
        # (= (Greater (S $x) (S $y)) (Greater $x $y))
        yield equation(S.Greater(succ(smaller), succ(larger))).to(
            S.Greater(smaller, larger)
        )

    one, two = succ(S.Z), succ(succ(S.Z))
    # !(test (Greater (S Z) (S Z)) false)
    assert m.fn.Greater(one, one) == [False]
    # !(test (Greater (S (S Z)) (S Z)) true)
    assert m.fn.Greater(two, one) == [True]
