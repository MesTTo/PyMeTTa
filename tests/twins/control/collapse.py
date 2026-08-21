"""The Python twin of examples/control/collapse.metta: collapsing one answer.

`(1 2 3)` is a term with three elements and no head to call, so it answers
itself, and `collapse` gathers the ONE answer into a one-element expression.
The doubled parentheses in the expected value are the whole point, and
`expr(expr(1, 2, 3))` writes them.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 596


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (collapse (1 2 3)) ((1 2 3)))
    yield m.eval(S.test(S["collapse"](expr(1, 2, 3)), expr(expr(1, 2, 3))))
