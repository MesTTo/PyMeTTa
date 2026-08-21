"""The Python twin of examples/basics/string.metta: a string is a value.

`val(text)` carries the Python string whole, which is how a MeTTa string
literal is written from Python. The parentheses inside it are characters,
not structure, which is the whole point of the original.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 419

TEXT = val("a test (with newlines and parentheses)")


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test "a test (with newlines and parentheses)" "...")
    yield m.eval(S.test(TEXT, TEXT))
