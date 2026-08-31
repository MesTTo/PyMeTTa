"""Purpose: examples/ch06-many-answers/08-permutations.metta in Python: 9! by joining inequalities.

Three kinds of knowledge, each written the way Python already writes it.

The 56 inequality FACTS are every ordered pair of distinct positions, so they
are a nested `for` and a tuple: MeTTa's `(1 != 2)` is Python's `(1, NE, 2)`, and
anything that yields tuples is a fact stream.

The nine `E` facts move one hole through the nine slots of a row, so the hole's
position is the loop variable and the row is built by slicing the eight
placeholders around it.

The 29-conjunct join is `space.match(...)`, whose varargs ARE the conjunction,
and the answer is a row per solution, so the example's
`(length (collapse (match ...)))` is `len()` over the view the door already
answers, counted through the engine rather than pulled into Python. The
conjuncts keep the original's triangular layout, which is this file's
documentation of the constraint graph.
"""

from metta import S, V

#: The inequality head, the hole, and the eight placeholder variables every
#: fact and the query share.
#:
#: The example's names are `$_1` and `___`, both of which carry a genuine
#: underscore: the factory attribute door maps every underscore to a hyphen,
#: so `V._1` would be `$-1` and these take the bracket, which is what rung 5
#: is for. `!=` has an operator word, so the head is `S.ne`.
NE = S.ne
HOLE = S["___"]
SLOT = (V["_1"], V["_2"], V["_3"], V["_4"], V["_5"], V["_6"], V["_7"], V["_8"])


def ne(left, right):
    """`($_left != $_right)`, one conjunct of the constraint graph."""
    return (SLOT[left - 1], NE, SLOT[right - 1])


def twin(m):
    """State 65 facts, then join them into every permutation of nine."""
    # Every ordered pair of distinct positions, the original's four rows of
    # fourteen.
    # (1 != 2) (1 != 3) ... (8 != 7)
    m += [
        (left, NE, right)
        for left in range(1, 9)
        for right in range(1, 9)
        if left != right
    ]

    # One hole, moved through the nine slots of a row.
    # (E $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 1 (___ $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8))
    # ... and eight more, the hole one place further along each time
    m += [
        S.E(*SLOT, slot, (*SLOT[: slot - 1], HOLE, *SLOT[slot - 1:]))
        for slot in range(1, 10)
    ]

    # The triangular constraint graph: each new position differs from every
    # earlier one, and the ninth slot is where the hole may sit.
    # !(test (length (collapse (match &self (, ($_1 != $_2) ... ) (state1 $state))))
    #        362880)
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
    assert len(m.match(*conjuncts)) == 362880


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 50760321 to 50760325, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 50760325 to 50760323, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 50760323 to 27172201 (-23588122): c7468b27 routed the
#: algebra carriers' counting through the algebra tower and this twin's
#: enumeration got 1.87x cheaper; the improvement was never re-pinned
#: when it landed [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 27172201
