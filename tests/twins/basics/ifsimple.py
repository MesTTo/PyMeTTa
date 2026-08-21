"""The Python twin of examples/basics/ifsimple.metta: two-argument `if`.

MeTTa's `if` takes an optional else branch, and with none it answers nothing
when the condition is false. Python's conditional expression always has one,
so the two-argument form is spelled at the term door instead.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 352


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if True 42) 42)
    yield m.eval(S.test(S["if"](TRUE, 42), 42))
