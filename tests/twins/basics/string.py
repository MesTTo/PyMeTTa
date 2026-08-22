"""examples/basics/string.metta in Python: a string is a value, not structure.

The parentheses in the text are characters, which is the whole point of the
original: evaluating a string literal answers that same string. `val(text)`
carries the Python string whole, which is how a MeTTa string literal is
written from Python.
"""

from petta import val

#: The text under test. Its parentheses and its spaces are DATA, and `val`
#: is what says so: every other string in a twin would be program text.
TEXT = val("a test (with newlines and parentheses)")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 443 to 141, -302 (-68.2%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, so the only
#: thing the engine is asked is what the string literal reduces to. Against
#: the example's 1849 the ratio is 0.0763 [measured 2026-08-22 min-of-3,
#: `twin_coverage.py --measure`]. The old figure priced a different
#: program.
BUDGET = 141


def twin(m):
    """Reduce a string literal, and get the same string back."""
    assert m.eval(TEXT) == [TEXT]
