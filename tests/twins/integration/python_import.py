"""The Python twin of examples/integration/python_import.metta: a .py import.

`import!` on a Python file registers its functions, and the twin evaluates the
same form. Its path is ABSOLUTE where the original writes it relative to the
`.metta` file, because an import written by a Python program has no importing
file to resolve against; the residue records that against P14.13, beside
import_duplicate_cycle, which meets the same wall.

The paths and the expected string answers cross as `val(...)`, the marked-data
door, since a bare string constant in a twin is what the lane refuses.
"""

from petta import S, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 2081


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self "_fixtures/python_import_file.py")
    yield m.eval(
        S["import!"](S["&self"],
            val("examples/integration/_fixtures/python_import_file.py"))
    )

    # !(test (repr (py-call (python_import_file.greet "PeTTa User"))) "Hello, PeTTa User from Python!")
    yield m.eval(
        S.test(S.repr(S["py-call"](S["python_import_file.greet"](val("PeTTa User")))),
            val("Hello, PeTTa User from Python!"))
    )

    # !(test (py-call (python_import_file.add 10 20)) 30)
    yield m.eval(S.test(S["py-call"](S["python_import_file.add"](10, 20)), 30))
