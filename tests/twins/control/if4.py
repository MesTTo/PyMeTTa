"""The Python twin of examples/control/if4.metta: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does. Every operand here is grounded, so each comparison is spelled
at the naming door rather than with a Python operator, which on two grounded
numbers is Python's own arithmetic.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 1108


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    yield m.eval(
        S.test(
            S["if"](
                S["if"](S["=="](42, 42), TRUE, FALSE),
                S["if"](TRUE, 42, S.lol),
                S["+"](2, 2),
            ),
            42,
        )
    )
