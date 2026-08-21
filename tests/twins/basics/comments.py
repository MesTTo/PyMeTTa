"""The Python twin of examples/basics/comments.metta: a nullary equation.

The original is about MeTTa's comment syntax, which has no Python analogue
to test; what survives translation is the definition it comments, `(= (f)
42)`, written here as a function of no arguments.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 2435


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def f():
        # (= (f) 42)
        return 42

    # !(test (f) 42)
    yield m.eval(S.test(f(), 42))
