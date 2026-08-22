"""examples/basics/identity.metta in Python: square a number, check the answer.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1249 to 2289 (+83.3%), by the twin contract change:
#: this file now says the definition as a decorated Python function rather
#: than as `equation(head).to(body)`, and `@m.define` pays a per-name
#: admission the container door never writes. Against the example's 2577 the
#: ratio is 0.8882, so the idiom is CHEAPER than the MeTTa it twins; the old
#: figure priced a different program.
BUDGET = 2289


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
        return x * x

    assert f(1) == [1]
