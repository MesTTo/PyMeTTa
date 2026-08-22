"""examples/reasoning/permutations.metta in Python: 9! by joining inequalities.

Three kinds of knowledge, each written the way Python already writes it.

The 56 inequality FACTS are every ordered pair of distinct positions, so they
are a nested `for` and a tuple: MeTTa's `(1 != 2)` is Python's `(1, NE, 2)`, and
anything that yields tuples is a fact stream.

The nine `E` facts move one hole through the nine slots of a row, so the hole's
position is the loop variable and the row is built by slicing the eight
placeholders around it. `___` cannot come from the `S` factory at all: the
namespace refuses every name beginning with `__` and the subscript door forwards
to the same guard, so the hole is `sym("___")` (residue, P14.5).

The 29-conjunct join stays one term, and this is the measured half. Python's own
conjunction door exists and is correct, `m[p1, p2, ...]`, but counting through it
means building 362,880 rows of ten bindings in Python: 41,213,543 inferences
against the engine's 17,626,820, +134%, far past the lane's 10% band
[measured 2026-08-22, ai-tmp/probe/f_perm_routes.py]. So the count stays
engine-side, the conjuncts keep the original's triangular layout, which is this
file's documentation of the constraint graph, and the missing door, a query that
aggregates before it crosses, is filed as friction.
"""

from petta import S, V, sym

#: Why this file sits below the top rung: the join's 362,880 rows cannot cross
#: into Python within the band, so the count stays a term.
RUNG = "counting the join's 362,880 rows through the Python conjunction door costs +134%, so the count stays engine-side"

#: The space the facts land in and the join reads, named as a symbol because a
#: term carries no handle.
SELF = S["&self"]

#: The inequality symbol, named once because it is neither a Python identifier
#: nor a Python operator here: `!=` on atoms is structural inequality, while
#: `(1 != 2)` in this example is a stored FACT with `!=` in the middle.
NE = S["!="]

#: The hole the nine `E` facts move through the nine positions of a row.
HOLE = sym("___")

#: The eight placeholder variables every fact and the query share.
SLOT = (V._1, V._2, V._3, V._4, V._5, V._6, V._7, V._8)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17626924 to 17626820, -104 (-0.0006%), by the twin
#: contract change: the `test` wrapper left the engine for Python's own
#: `assert`, which is all that could move; the join is the example. Against the
#: example's 18015290 the ratio is 0.9784 [measured 2026-08-22 min-of-3:
#: `twin_coverage.py --measure examples/reasoning/permutations.metta`]. Prior:
#: ADDED 2026-08-22 at 17626924 by the wave-3 twin baseline.
BUDGET = 17626820


def ne(left, right):
    """`($_left != $_right)`, one conjunct of the constraint graph."""
    return (SLOT[left - 1], NE, SLOT[right - 1])


def twin(m):
    """State 65 facts, then join them into every permutation of nine."""
    # Every ordered pair of distinct positions, the original's four rows of
    # fourteen.
    for left in range(1, 9):
        for right in range(1, 9):
            if left != right:
                m += (left, NE, right)

    # One hole, moved through the nine slots of a row.
    for slot in range(1, 10):
        m += S.E(*SLOT, slot, (*SLOT[: slot - 1], HOLE, *SLOT[slot - 1:]))

    # The triangular constraint graph: each new position differs from every
    # earlier one, and the ninth slot is where the hole may sit.
    conjuncts = (
        ne(1, 2),
        ne(2, 3), ne(3, 1),
        ne(3, 4), ne(4, 2), ne(4, 1),
        ne(4, 5), ne(5, 3), ne(5, 2), ne(5, 1),
        ne(5, 6), ne(6, 4), ne(6, 3), ne(6, 2), ne(6, 1),
        ne(6, 7), ne(7, 5), ne(7, 4), ne(7, 3), ne(7, 2), ne(7, 1),
        ne(7, 8), ne(8, 6), ne(8, 5), ne(8, 4), ne(8, 3), ne(8, 2), ne(8, 1),
        S.E(*SLOT, V.x, V.state),
    )
    assert m.eval(
        S.length(S.collapse(S.match(SELF, S[","](*conjuncts), S.state1(V.state))))
    ) == [362880]
