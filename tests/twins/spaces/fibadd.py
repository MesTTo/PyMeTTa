"""The Python twin of examples/spaces/fibadd.metta: an added equation is a real one.

The exponential fib(30) tree outruns the evaluator's default fuel, and the point
of the example is that this is just as true of an equation that ARRIVED through
`add-atom` at run time as of one written in the file.

`@m.define` is that arrival in Python: the decorator reads the body as syntax and
writes the equation into the space, so the recursion below IS the equation, and
`with-pragma!` raises the bound over the call exactly as it does in the original.
The write form answers the unit; the assertion after it is what runs the tree.
"""

from petta import S, expr

#: The answer group a write form contributes. `add-atom` answers the unit, and
#: the unit is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 28277895 to 28278972, +1077 (+0.004%), by the P14
#: twin-style rewrite: the equation now arrives through @m.define instead of
#: through an evaluated (add-atom &self (= ...)) term, so the delta is the
#: decorator door's definition-time price NET of the term it replaces. Against
#: 28.3 million inferences of fib(30) that is four thousandths of a percent,
#: which is this folder's cleanest statement of where the decorator's cost
#: lives: all of it at definition, none of it per call. The ratio against the
#: original is 0.9999.
#: Prior: ADDED 2026-08-22 at 28277895 by the wave-3 spaces baseline.
BUDGET = 28278972


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    # !(add-atom &self (= (fib $N) (if (< $N 2) $N
    #                                  (+ (fib (- $N 1)) (fib (- $N 2))))))
    @m.define
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    yield WROTE

    # !(test (with-pragma! ((max-stack-depth 100000000)) (fib 30)) 832040)
    yield m.eval(
        S.test(
            S["with-pragma!"]((S["max-stack-depth"](100000000),), S.fib(30)),
            832040,
        )
    )
