"""The Python twin of examples/control/if.metta: three-argument `if`.

Both arms are EXPRESSIONS, `(3 4)` and `(5 6)`, so `expr(...)` builds them;
`(3, 4)` would be a Python tuple and never reaches the engine as a term.

The condition is a term over two grounded numbers, which the naming door
spells: `1 > 2` in Python is Python's own comparison and answers `False`
before any atom exists, so `S[">"](1, 2)` is how a comparison stays a term.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 852


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (> 1 2) (3 4) (5 6)) (5 6))
    yield m.eval(
        S.test(S["if"](S[">"](1, 2), expr(3, 4), expr(5, 6)), expr(5, 6))
    )
