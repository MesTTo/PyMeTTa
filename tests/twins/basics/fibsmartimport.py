"""The Python twin of examples/basics/fibsmartimport.metta: importing a module.

`import!` is a directive in a `.metta` file and has no dedicated Python door,
so it is built as the term it is. A bare module name resolves relative to the
IMPORTING FILE, and a Python-authored program has no file, so the twin names
the path instead; the residue table records that against P14.13.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 10033


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self fibsmart) answers (())
    yield m.eval(S["import!"](S["&self"], S["examples/basics/fibsmart"]))
    # !(test (fib 100) 354224848179261915075)
    yield m.eval(S.test(S.fib(100), 354224848179261915075))
