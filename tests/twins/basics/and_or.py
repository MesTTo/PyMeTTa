"""The Python twin of examples/basics/and_or.metta: boolean connectives.

`&` and `|` on a built term are MeTTa's `and` and `or`: the operator table
lowers them, so the Python operators write the s-expression the example
writes by hand.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 943


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (or (and true false) true) 1 2) 1)
    yield m.eval(S.test(S["if"](S["and"](TRUE, FALSE) | TRUE, 1, 2), 1))
