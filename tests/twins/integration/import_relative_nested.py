"""examples/integration/import_relative_nested.metta in Python: one import, two files deep.

`root.metta` imports a sibling and a file in a subdirectory, and both of those
imports resolve against the file that wrote them rather than against the
process. Importing `root` alone therefore has to bring in all three, which is
what the two claims check.

The path is written from the repository root because a Python program has no
importing file to resolve against, and `import!` names its space as a symbol
because no import door hangs off the space handle. Both are residue.
"""

from petta import S

#: The space the import writes, and the fixture it reads, from the repository
#: root: the lane runs there.
SELF = S["&self"]  # rung: no import door hangs off the space handle
ROOT = S["examples/integration/_fixtures/imports/relative/root"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8459 to 7394, -1065 (-12.6%), by the twin contract
#: change: two `test` wrappers left the engine for Python's own `assert` and
#: the calls under them became `m.fn(name)()`. The import itself is most of
#: what is left, which is why the drop is small. Against the example's 10151 the
#: ratio is 0.7284 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/integration/import_relative_nested.metta`]. Prior: ADDED 2026-08-22
#: at 8459 by the wave-3 twin baseline, which priced a transliteration.
BUDGET = 7394


def twin(m):
    """Import the root, then ask the two files it reached."""
    m.eval(S["import!"](SELF, ROOT))

    assert m.fn("from-sibling")() == 42
    assert m.fn("from-second")() == 7
