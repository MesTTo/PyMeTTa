"""examples/data/constanthead.metta in Python: a structure in a head.

`h` matches when its first argument IS `(justdata haha $B)`, binding `$B` out
of the middle of it, and adds that to its second. Selecting on a structure in a
head position is what the clause does, and it is why the clause is written as
an equation: a compiled parameter list carries plain names, and a default there
is a head pattern that must be a LITERAL, a constant IN a position rather than
a structure around one.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1593 to 1448, -145 (-9.10%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`; the structural
#: clause and the one call over it are unchanged. Against the example's 3616
#: the ratio is 0.4004 [measured 2026-08-22 min-of-3: `twin_coverage.py
#: --measure examples/data/constanthead.metta`]. Prior: the file's first pin,
#: uncommented.
BUDGET = 1448


def twin(m):
    """Define the structural clause, then feed it the structure it wants."""
    m += equation(S.h(S.justdata(S.haha, V.B), V.C)).to(V.B + V.C)

    assert m.fn("h")(S.justdata(S.haha, 30), 40) == 70
