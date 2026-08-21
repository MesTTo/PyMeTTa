"""The Python twin of examples/basics/identity.metta: one equation, one call.

`@m.define` reads the body as syntax, so `x * x` IS `(* $x $x)`.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 2762


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def f(x):
        # (= (f $x) (* $x $x))
        return x * x

    # !(test (f 1) 1)
    yield m.eval(S.test(f(1), 1))
