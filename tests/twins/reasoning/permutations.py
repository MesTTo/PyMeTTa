"""Purpose: examples/reasoning/permutations.metta in Python: 9! by joining inequalities.

Three kinds of knowledge, each written the way Python already writes it.

The 56 inequality FACTS are every ordered pair of distinct positions, so they
are a nested `for` and a tuple: MeTTa's `(1 != 2)` is Python's `(1, NE, 2)`, and
anything that yields tuples is a fact stream.

The nine `E` facts move one hole through the nine slots of a row, so the hole's
position is the loop variable and the row is built by slicing the eight
placeholders around it.

The 29-conjunct join is Python's own conjunction door, the comma inside a
subscript, and the answer is a row per solution, so the example's
`(length (collapse (match ...)))` is `len()` over what the door already
answers. The conjuncts keep the original's triangular layout, which is this
file's documentation of the constraint graph.
"""

from metta import S, V

#: The inequality head, the hole, and the eight placeholder variables every
#: fact and the query share.
#:
#: The example's names are `$_1` and `___`, both of which carry a genuine
#: underscore: the factory attribute door maps every underscore to a hyphen,
#: so `V._1` would be `$-1` and these take the bracket, which is what rung 5
#: is for.
NE = S["!="]
HOLE = S["___"]
SLOT = (V["_1"], V["_2"], V["_3"], V["_4"], V["_5"], V["_6"], V["_7"], V["_8"])

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


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
    assert len(m[conjuncts]) == 362880
