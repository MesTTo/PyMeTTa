"""The Python twin of examples/integration/import_relative_nested.metta.

One import, two definitions reached through it: `root` imports a sibling and a
nested subdirectory, and both resolve.

The imported path is ABSOLUTE where the original writes it relative to the
`.metta` file, because an import written by a Python program has no importing
file to resolve against; the residue records that against P14.13, beside
import_duplicate_cycle, which meets the same wall.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 8459


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self _fixtures/imports/relative/root)
    yield m.eval(
        S["import!"](S["&self"],
            S["examples/integration/_fixtures/imports/relative/root"])
    )

    # !(test (from-sibling) 42)
    yield m.eval(S.test(S["from-sibling"](), 42))

    # !(test (from-second) 7)
    yield m.eval(S.test(S["from-second"](), 7))
