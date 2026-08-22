"""examples/types/recursive_types2.metta in Python: Peano numbers and a test.

`Nat` is `Z` or `(S n)` for a `Nat`, and `Greater` walks two of them down in
step until one runs out. The three clauses select on the SHAPE of their
arguments, `(S $x)` against `Z`, which a compiled parameter list cannot say: a
head pattern there is a literal default, a constant IN a position rather than a
structure around one. So the clauses are written as the equations they are.

The constructor pair is declared rather than recorded for the same kind of
reason plus one more: a Python class declares ITSELF as what its constructor
returns, where `(: S (-> Nat Nat))` declares the ADT the constructor belongs
to, and the constructor here is spelled `S`, which is already the name of the
symbol factory in Python.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9213 to 8949, -264 (-2.87%), by the twin-shape
#: rewrite: the two `test` wrappers left the engine for `assert`; the Peano
#: walk is the same six atoms and the same two calls. Against the example's
#: 13131 the ratio is 0.6815 [measured 2026-08-22 min-of-3: `twin_coverage.py
#: --measure examples/types/recursive_types2.metta`]. Prior: RE-PINNED at
#: 9213 by the lift onto @rules plus one m.add(*group).
BUDGET = 8949


def twin(m):
    """Build two Peano numbers and compare them."""
    typed, arrow = S[":"], S["->"]
    succ = S.S

    m += typed(S.Z, S.Nat)
    m += typed(succ, arrow(S.Nat, S.Nat))
    m += typed(S.Greater, arrow(S.Nat, S.Nat, S.Bool))
    m += equation(S.Greater(succ(V.x), S.Z)).to(True)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    m += equation(S.Greater(S.Z, V.x)).to(False)  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
    m += equation(S.Greater(succ(V.x), succ(V.y))).to(S.Greater(V.x, V.y))

    one, two = succ(S.Z), succ(succ(S.Z))
    assert m.fn("Greater")(one, one) is False
    assert m.fn("Greater")(two, one) is True
