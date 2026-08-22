"""The Python twin of examples/spaces/spaces_find.metta: find as a branch filter.

`find` from lib_spaces succeeds once per matching row, so the nested ifs answer
one `(FoundChain a b c)` for the chain that continues and one
`(MissedSecondPiece)` for the row that does not.

`import!` stays a term because it is a directive rather than a value door: there
is no Python spelling for it yet, and the residue names the gap (P14.13). The two
facts are plain tuples, which is what the knowledge front reads.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 20742 across the P14 twin-style rewrite: the two facts
#: now enter as tuples and every term is built from named symbols, and both
#: store and evaluate exactly what the nested expr() spellings did. Measured
#: 20742 before and after, which also says the import! directive is where this
#: file's cost lives rather than in any of its own forms.
#: Prior: ADDED 2026-08-22 at 20742 by the wave-3 spaces baseline.
BUDGET = 20742


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # !(import! &self (library lib_spaces))
    yield m.eval(S["import!"](here, S.library(S.lib_spaces)))

    # (friend a b) (friend b c)
    m += (S.friend, S.a, S.b)
    m += (S.friend, S.b, S.c)

    # !(test (collapse (if (find &self (friend $a $b))
    #                      (if (find &self (friend $b $c))
    #                          (FoundChain $a $b $c)
    #                          (MissedSecondPiece))
    #                      (MissedAllPieces)))
    #        ((FoundChain a b c) (MissedSecondPiece)))
    yield m.eval(
        S.test(
            S.collapse(
                S["if"](
                    S.find(here, S.friend(V.a, V.b)),
                    S["if"](
                        S.find(here, S.friend(V.b, V.c)),
                        S.FoundChain(V.a, V.b, V.c),
                        S.MissedSecondPiece(),
                    ),
                    S.MissedAllPieces(),
                )
            ),
            (S.FoundChain(S.a, S.b, S.c), S.MissedSecondPiece()),
        )
    )
