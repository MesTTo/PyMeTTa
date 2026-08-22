"""examples/basics/fibsmartimport.metta in Python: importing another file.

`import!` is a directive in a `.metta` file and has no Python door of its own,
so it is built as the term it is, and the imported file's own claim runs as
part of the import.

Two things it will not take. A bare module name resolves relative to the
IMPORTING FILE and a Python-authored program has no file, so the path is
named in full; and the space it imports INTO has to be the symbol `&self`,
because handing it the space handle fails inside the loader. The residue
table records both against P14.13.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10566 to 9942, -624 (-5.9%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`; the import
#: itself, which runs the imported file's own claim, is most of what is
#: left. Against the example's 11976 the ratio is 0.8302 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 9942


def twin(m):
    """Import the accumulator fib, then run it."""
    # (import! &self fibsmart)
    m.eval(S["import!"](S["&self"], S["examples/basics/fibsmart"]))  # rung: space as a symbol

    assert m.fn("fib")(100) == 354224848179261915075
