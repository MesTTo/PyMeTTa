"""The Python twin of examples/control/caseconstrain.metta: a cons pattern.

One case, whose pattern `(cons $h $t)` decomposes the key `(1 2 3)` into head
and tail, so the branch answers 1.

The cases of a `case` are SYNTAX, matched rather than evaluated, which is why
they are built as terms: `expr(expr(pattern, value))` is the list of one pair.
Python's own `match`/`case` statement has no lowering in the compiled subset,
which the residue table records against P14.4.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 576


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (case (1 2 3) ( ( (cons $h $t) $h) ) ) 1)
    yield m.eval(
        S.test(
            S["case"](
                expr(1, 2, 3),
                expr(expr(S.cons(V.h, V.t), V.h)),
            ),
            1,
        )
    )
