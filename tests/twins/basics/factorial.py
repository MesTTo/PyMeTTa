"""The Python twin of examples/basics/factorial.metta: recursion over if.

`@m.define` reads the function as syntax and writes the equation, so the
Python `if`/`else` expression IS MeTTa's `if` and the recursive call is the
same call the equation makes.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 4420


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define(name="facF")
    def fac_f(n):
        # (= (facF $n) (if (== $n 0) 1 (* $n (facF (- $n 1)))))
        return 1 if n == 0 else n * fac_f(n - 1)

    # !(test (facF 10) 3628800)
    yield m.eval(S.test(fac_f(10), 3628800))
