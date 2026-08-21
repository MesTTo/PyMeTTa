"""The Python twin of examples/basics/fibsmart.metta: the accumulator fib.

Two equations by two doors, and the reason is a real hole. `fib-tr` compiles
from Python because a body may name ITSELF in either spelling. `fib` cannot,
because a compiled body resolves a free name EXACTLY and the engine knows
`fib-tr`, not `fib_tr`; so the second equation is added as the atom it is,
`m += S["="](head, body)`, which is the container protocol writing a bare
equation with no string anywhere.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
BUDGET = 7740


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define(name="fib-tr")
    def fib_tr(n, a, b):
        # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
        return a if n == 0 else fib_tr(n - 1, b, a + b)

    # (= (fib $n) (fib-tr $n 0 1))
    m += S["="](S.fib(V.n), S["fib-tr"](V.n, 0, 1))

    # !(test (fib 100) 354224848179261915075)
    yield m.eval(S.test(S.fib(100), 354224848179261915075))
