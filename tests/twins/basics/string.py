"""examples/basics/string.metta in Python: a string is a value, not structure.

The parentheses in the text are characters, which is the whole point of the
original: evaluating a string literal answers that same string. `ground(text)`
carries the Python string whole, which is how a MeTTa string literal is
written from Python.
"""

from metta import ground

#: The text under test. Its parentheses and its spaces are DATA, and `ground`
#: is what says so: every other string in a twin would be program text.
TEXT = ground("a test (with newlines and parentheses)")

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Reduce a string literal, and get the same string back."""
    assert m.eval(TEXT) == [TEXT]
