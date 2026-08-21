"""The Python twin of examples/basics/booleansolver.metta: solving for a bool.

`and` and `or` run backwards, so an unbound variable is SOLVED FOR rather
than read.

`V.x` is the variable `$x`. Both answers come back from one form, which is
what a nondeterministic answer set is.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 1182


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (and (or $x True) $y) ($x $y)) ((True True) (False True)))
    yield m.eval(
        S.test(
            S["if"]((V.x | TRUE) & V.y, expr(V.x, V.y)),
            expr(expr(TRUE, TRUE), expr(FALSE, TRUE)),
        )
    )
