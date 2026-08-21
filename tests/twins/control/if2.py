"""The Python twin of examples/control/if2.metta: a symbol is not a variable.

`(is-var a)` asks about the ATOM `a`, so the answer is False and the else arm
runs. `S.a` is that atom; a Python name `a` would be a Python binding and
never reach the engine.

The then arm `(() (+ 1 1))` is an expression whose first element is the empty
expression, which `expr(expr(), ...)` spells: `()` is a term, not a hole.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 1138


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (is-var a) (() (+ 1 1)) (+ 2 2)) 4)
    yield m.eval(
        S.test(
            S["if"](
                S["is-var"](S.a),
                expr(expr(), S["+"](1, 1)),
                S["+"](2, 2),
            ),
            4,
        )
    )
