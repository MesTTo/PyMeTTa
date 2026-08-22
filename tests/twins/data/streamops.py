"""The Python twin of examples/data/streamops.metta.

The same four set operations as multiset_operations.metta, over
NONDETERMINISM rather than over expressions: `unique-atom` walks an
expression, while `unique` walks a superposition and needs a `collapse` to
become one answer again.

The twin is the term door throughout: a symbol calls to build, and a plain
Python tuple is the expression it is called on.
"""

from petta import S

#: The symbols these superpositions are built from, bound once so a line reads
#: as the multiset it is rather than as five repetitions of the factory.
a, b, c, d = S.a, S.b, S.c, S.d

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4650 to 4650, +0, by the wave-4 idiom rewrite: the
#: forms are the same terms built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 4650


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(test (collapse (unique (superpose (a b c d d)))) (a b c d))
    yield m.eval(
        S.test(S.collapse(S.unique(S.superpose((a, b, c, d, d)))), (a, b, c, d))
    )
    # !(test (collapse (union (superpose (a b b c)) (superpose (b c c d))))
    #        (a b b c b c c d))
    yield m.eval(
        S.test(
            S.collapse(S.union(S.superpose((a, b, b, c)), S.superpose((b, c, c, d)))),
            (a, b, b, c, b, c, c, d),
        )
    )
    # !(test (collapse (intersection (superpose (a b c c)) (superpose (b c c c d))))
    #        (b c c))
    yield m.eval(
        S.test(
            S.collapse(
                S.intersection(S.superpose((a, b, c, c)), S.superpose((b, c, c, c, d)))
            ),
            (b, c, c),
        )
    )
    # !(test (collapse (subtraction (superpose (a b b c)) (superpose (b c c d))))
    #        (a b))
    yield m.eval(
        S.test(
            S.collapse(
                S.subtraction(S.superpose((a, b, b, c)), S.superpose((b, c, c, d)))
            ),
            (a, b),
        )
    )
