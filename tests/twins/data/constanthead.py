"""examples/data/constanthead.metta in Python: a structure in a head.

`h` matches when its first argument IS `(justdata haha $B)`, binding `$B` out
of the middle of it, and adds that to its second. Selecting on a structure in a
head position is what the clause does, and it is why the clause is written as
an equation: a compiled parameter list carries plain names, and a default there
is a head pattern that must be a LITERAL, a constant IN a position rather than
a structure around one.
"""

from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Define the structural clause, then feed it the structure it wants."""
    m += equation(S.h(S.justdata(S.haha, V.B), V.C)).to(V.B + V.C)

    assert m.fn.h(S.justdata(S.haha, 30), 40).one() == 70
