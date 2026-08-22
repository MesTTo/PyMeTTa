"""examples/spaces/spacefunction.metta in Python: removing a definition.

Two identical equations under different names, one of them removed. The removal
takes the compiled answer with it, so `(f 3 4)` becomes its own answer while
`(g 3 4)` still reduces to 7, and a plain fact behaves the same way.

That is the reflectivity invariant in Python dress: a Python-authored
definition is an ordinary atom, so `-=`, the operator that removes an atom,
removes it, and `equation(head).to(body)` names which atom to remove.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5426 to 3981, -1445 (-26.6%), by the twin contract
#: change: three `(test ...)` terms became three Python `assert`s, so the
#: `test` and `collapse` wrappers and the last form's `match` all left the
#: engine, replaced by `not in` over the container door. What did NOT move is
#: the two definitions and the two removals. Against the example's 8288 the
#: ratio is 0.4803.
#: Prior: 5426, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3981


def twin(m):
    """Define two functions, remove one, and see which answers survive."""

    @m.define
    def f(x, y):
        return x + y

    @m.define
    def g(x, y):
        return x + y

    # An equation is an ordinary atom, so the operator that removes an atom
    # removes it, and the compiled clause leaves with the atom.
    m -= equation(S.f(V.x, V.y)).to(V.x + V.y)

    # With nothing left to reduce it, the call is its own answer.
    assert m.eval(S.f(3, 4)) == [S.f(3, 4)]
    assert g(3, 4) == [7]

    # A plain fact is the same story with no compilation in it.
    m += (S.my, S.test)
    m -= (S.my, S.test)
    assert (S.my, S.test) not in m
