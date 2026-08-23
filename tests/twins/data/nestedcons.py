"""examples/data/nestedcons.metta in Python: two cons cells in one head.

`(cons $a (cons $b $L))` takes an expression apart twice over and answers the
second element. The head is nested structure, which a compiled parameter list
cannot spell, so the clause is written as the equation it is; the call then
reads `(a b c d)` as head `a`, then `(b c d)` as head `b`, and answers `b`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Define the doubly-nested clause and take the second element with it."""
    m += equation(S.f(S.cons(V.a, S.cons(V.b, V.L)))).to(V.b)

    assert m.fn.f(S.a(S.b, S.c, S.d)).one() == S.b
