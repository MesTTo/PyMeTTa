"""The Python twin of examples/basics/fib.metta: the exponential fib, budgeted.

The deliberately exponential tree exceeds the evaluator's default fuel, so
the original scopes a larger `max-stack-depth` to the one expression with
`with-pragma!`. That form takes its settings UNEVALUATED, which is why it is
built at the term door rather than called.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 25585349


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    # !(test (with-pragma! ((max-stack-depth 100000000)) (fib 30)) 832040)
    yield m.eval(
        S.test(
            S["with-pragma!"](
                expr(expr(S["max-stack-depth"], 100000000)), fib(30)
            ),
            832040,
        )
    )
