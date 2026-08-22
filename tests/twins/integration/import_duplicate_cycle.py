"""examples/integration/import_duplicate_cycle.metta in Python: importing twice, and in a circle.

One file imported under two spellings of its path loads ONCE, so the marker it
adds is there once and not twice; and two files that import each other both
finish, so both of their functions answer.

The paths are written from the repository root, which also flattens the `./`
and `.` segments the example's second form exists to exercise: a Python program
has no importing file to resolve a relative import against. That, and `import!`
naming its space as a symbol, are the residue this file carries.
"""

from petta import S

#: The space every import writes, and the same file twice: once by module name
#: and once with its suffix. Written from the repository root, where the lane
#: runs.
SELF = S["&self"]  # rung: no import door hangs off the space handle
DUPLICATE = S["examples/integration/_fixtures/imports/overhaul/duplicate"]
DUPLICATE_METTA = S["examples/integration/_fixtures/imports/overhaul/duplicate.metta"]
CYCLE = S["examples/integration/_fixtures/imports/overhaul/cycle_a"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8602 to 6920, -1682 (-19.6%), by the twin contract
#: change: three `test` wrappers and a `collapse` left the engine for Python's
#: own `assert` and list comparison; the three imports did not move. Against
#: the example's 11911 the ratio is 0.5810 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure
#: examples/integration/import_duplicate_cycle.metta`]. Prior: ADDED 2026-08-22
#: at 8602 by the wave-3 twin baseline, which priced a transliteration.
BUDGET = 6920


def twin(m):
    """Import one file twice and a cycle once, then read all three."""
    for target in (DUPLICATE, DUPLICATE_METTA, CYCLE):
        m.eval(S["import!"](SELF, target))

    # Loaded once, so the marker answers once.
    assert m.eval(S["duplicate-import-result"]()) == [S["loaded-once"]]

    # Both halves of the cycle finished loading.
    assert m.fn("cycle-a")() == S.a
    assert m.fn("cycle-b")() == S.b
