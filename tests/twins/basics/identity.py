"""The Python twin of examples/basics/identity.metta: one equation, one call.

The equation is written at the container door, `m += S["="](head, body)`,
the cheapest of the two pure-Python spellings: `@m.define` reads a body as
syntax and pays a fixed registration cost (measured +1,561 inferences per
definition) that dominates an example this small, while the bare equation
lands the identical atom for the identical compiled clauses. The ladder
documents both rungs; a twin picks the one the original's size calls for.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
BUDGET = 1214


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (f $x) (* $x $x))
    m += S["="](S.f(V.x), V.x * V.x)

    # !(test (f 1) 1)
    yield m.eval(S.test(S.f(1), 1))
