"""The Python twin of examples/data/constanthead.metta: a constant in a head.

`h` expects a STRUCTURE in its first argument, `(justdata haha $B)`, so the
head both selects on the constant `haha` and binds `$B` out of the same term.

The clause stays at the container door because that head argument is a
PATTERN. A compiled definition spells a head pattern as a literal default,
`def fib(n=0)`, which reaches a constant in a position and not a structure
around one, so the residue table records the missing spelling against P14.4.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
BUDGET = 1593


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # h just expects a structure:
    # (= (h (justdata haha $B) $C) (+ $B $C))
    m += equation(S.h(S.justdata(S.haha, V.B), V.C)).to(V.B + V.C)

    # just structure matching (check out listhead.metta for list structure matching)
    # !(test (h (justdata haha 30) 40) 70)
    yield m.eval(S.test(S.h(S.justdata(S.haha, 30), 40), 70))
