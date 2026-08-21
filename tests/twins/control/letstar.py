"""The Python twin of examples/control/letstar.metta: sequential bindings.

Inside a compiled body, `x = 1` IS a `let*` binding: the decorator folds a
statement list into nested `let*` around what follows it. This file has no
definition to hang statements on, though, so the form is built as the term it
is, one `(pattern value)` pair per binding.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 714


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    yield m.eval(
        S.test(
            S["let*"](
                expr(expr(V.x, 1), expr(V.y, 2)),
                S["+"](V.x, V.y),
            ),
            3,
        )
    )
