"""The Python twin of examples/reasoning/permutations.metta: 9! by joining.

Three kinds of knowledge, each written the way Python already writes it.

The 56 inequality FACTS are every ordered pair of distinct positions, so they
are a nested `for` and a tuple: MeTTa's `(1 != 2)` is Python's `(1, NE, 2)`,
and anything that yields tuples is a fact stream.

The nine `E` facts move one hole through the nine slots of a row, so the hole's
position is the loop variable and the row is built by slicing the eight
placeholders around it. `___` cannot come from the `S` factory at all: the
namespace refuses every name beginning with `__`, and the subscript door
forwards to the same guard, so the hole is `sym("___")`. That is filed as
residue against P14.5.

The query stays one term because a `match` conjunction IS a term: the 28
conjuncts keep the original's own triangular layout, which is the file's
documentation of the constraint graph, with `ne(left, right)` naming the
`($_left != $_right)` shape so a row still fits on a line.
"""

from petta import S, V, sym

#: The inequality symbol, named once because it is neither a Python identifier
#: nor a Python operator here: `!=` on atoms is structural inequality, and
#: `(1 != 2)` in this example is a stored FACT with `!=` in the middle rather
#: than a comparison term with `!=` at the head.
NE = S["!="]

#: The hole the nine `E` facts move through the nine positions of a row.
HOLE = sym("___")

#: The eight placeholder variables every fact and the query share.
SLOT = (V._1, V._2, V._3, V._4, V._5, V._6, V._7, V._8)

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 17626924 across the rewrite: the loops and tuples build
#: the same 65 atoms the unrolled `expr` calls built, which the atom-level
#: differential confirms byte-for-byte. Prior: ADDED 2026-08-22 at 17626924 by
#: the wave-3 twin baseline.
BUDGET = 17626924


def ne(left, right):
    """`($_left != $_right)`, the query's own inequality conjunct."""
    return (SLOT[left - 1], NE, SLOT[right - 1])


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (1 != 2) (1 != 3) ... (8 != 6) (8 != 7): every ordered pair of distinct
    # positions, the original's four rows of fourteen.
    for left in range(1, 9):
        for right in range(1, 9):
            if left != right:
                m += (left, NE, right)

    # (E $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 1 (___ $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8))
    # ... through ...
    # (E $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 9 ($_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 ___))
    for slot in range(1, 10):
        m += S.E(*SLOT, slot, (*SLOT[: slot - 1], HOLE, *SLOT[slot - 1 :]))

    # !(test (length (collapse (match &self
    #                                 (, ($_1 != $_2)
    #                                    ($_2 != $_3) ($_3 != $_1)
    #                                    ($_3 != $_4) ($_4 != $_2) ($_4 != $_1)
    #                                    ($_4 != $_5) ($_5 != $_3) ($_5 != $_2) ($_5 != $_1)
    #                                    ($_5 != $_6) ($_6 != $_4) ($_6 != $_3) ($_6 != $_2) ($_6 != $_1)
    #                                    ($_6 != $_7) ($_7 != $_5) ($_7 != $_4) ($_7 != $_3) ($_7 != $_2) ($_7 != $_1)
    #                                    ($_7 != $_8) ($_8 != $_6) ($_8 != $_5) ($_8 != $_4) ($_8 != $_3) ($_8 != $_2) ($_8 != $_1)
    #                                    (E $_1 $_2 $_3 $_4 $_5 $_6 $_7 $_8 $x $state))
    #                                 (state1 $state))))
    #        362880)
    yield m.eval(
        S.test(
            S.length(
                S.collapse(
                    S.match(
                        S["&self"],
                        S[","](
                            ne(1, 2),
                            ne(2, 3), ne(3, 1),
                            ne(3, 4), ne(4, 2), ne(4, 1),
                            ne(4, 5), ne(5, 3), ne(5, 2), ne(5, 1),
                            ne(5, 6), ne(6, 4), ne(6, 3), ne(6, 2), ne(6, 1),
                            ne(6, 7), ne(7, 5), ne(7, 4), ne(7, 3), ne(7, 2), ne(7, 1),
                            ne(7, 8), ne(8, 6), ne(8, 5), ne(8, 4), ne(8, 3), ne(8, 2), ne(8, 1),
                            S.E(*SLOT, V.x, V.state),
                        ),
                        S.state1(V.state),
                    )
                )
            ),
            362880,
        )
    )
