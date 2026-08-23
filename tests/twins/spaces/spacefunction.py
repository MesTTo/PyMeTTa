"""Purpose: examples/spaces/spacefunction.metta in Python: removing a definition.

Two identical equations under different names, one of them removed. The removal
takes the compiled answer with it, so `(f 3 4)` becomes its own answer while
`(g 3 4)` still reduces to 7, and a plain fact behaves the same way.

That is the reflectivity invariant in Python dress: a Python-authored
definition is an ordinary atom, so `-=`, the operator that removes an atom,
removes it, and `equation(head).to(body)` names which atom to remove.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


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
