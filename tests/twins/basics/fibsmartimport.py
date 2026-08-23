"""examples/basics/fibsmartimport.metta in Python: importing another file.

`import!` is a directive in a `.metta` file and has no Python door of its own,
so it is built as the term it is, and the imported file's own claim runs as
part of the import. The space it imports INTO is the handle itself: a space
handle is a grounded atom and crosses term positions as one, so no `&self`
symbol appears here.

One thing it will not take. A bare module name resolves relative to the
IMPORTING FILE and a Python-authored program has no file, so the path is named
in full; the residue table records that against P14.13.

What the import brings in is then an ordinary callable: `m.fn.fib` is the
imported function, named through the space that now holds it.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Import the accumulator fib, then run it."""
    # (import! &self fibsmart)
    m.eval(S["import!"](m, S["examples/basics/fibsmart"]))

    # COST, the library's rather than this twin's: naming `fib` through the
    # space resolves a handle against the engine (~1,206 inferences) and the
    # first answer view sets up a held evaluation (~4,700), which is the whole
    # of this twin's 16,564 against the example's 12,672. The spelling is the
    # right one [measured 2026-08-23 on this worktree; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    assert m.fn.fib(100) == [354224848179261915075]
