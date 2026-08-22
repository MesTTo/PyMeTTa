"""The Python twin of examples/integration/import_duplicate_cycle.metta.

The same file imported twice, once by a path with `./` and `.` segments in it,
loads once; and a two-file import cycle terminates with both halves defined.

The imported paths are ABSOLUTE where the original writes them relative to the
`.metta` file, which also flattens the `./` and `.` segments the second form
exists to exercise: an import written by a Python program has no importing file
to resolve against. The residue records that against P14.13.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 8602


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self _fixtures/imports/overhaul/duplicate)
    yield m.eval(
        S["import!"](S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/duplicate"])
    )

    # !(import! &self ./_fixtures/imports/overhaul/./duplicate.metta)
    yield m.eval(
        S["import!"](S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/duplicate.metta"])
    )

    # !(import! &self _fixtures/imports/overhaul/cycle_a)
    yield m.eval(
        S["import!"](S["&self"],
            S["examples/integration/_fixtures/imports/overhaul/cycle_a"])
    )

    # !(test (collapse (duplicate-import-result)) (loaded-once))
    yield m.eval(
        S.test(S.collapse(S["duplicate-import-result"]()),
            (S["loaded-once"],))
    )

    # !(test (cycle-a) a)
    yield m.eval(S.test(S["cycle-a"](), S.a))

    # !(test (cycle-b) b)
    yield m.eval(S.test(S["cycle-b"](), S.b))
