"""The Python twin of examples/translation/translatepredicate.metta.

`translatePredicate` compiles a Prolog goal into the running program, so the
two goals here are `is(X, 2)` and `+(X, 40, Z)`, and `progn` runs them in
order and answers `$z`.

The form is the term door because it is a runnable form and not a definition.
`+` is named rather than reached through Python's operator because it appears
here as a THREE-PLACE RELATION: Python's `+` is binary and left-associating,
so `V.x + 40 + V.z` would build `(+ (+ $x 40) $z)`, a different term. The
residue table records the missing spelling against P14.4.
"""

from petta import S, V

#: `+` as the three-place Prolog relation this goal names, not as arithmetic.
plus = S["+"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 685 to 685, +0, by the wave-4 idiom rewrite: the form
#: is the same term built at the same door, so the rewrite is a SPELLING
#: change and the counter says so.
BUDGET = 685


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(test (progn (translatePredicate (is $x 2))
    #               (translatePredicate (+ $x 40 $z)) $z)
    #        42)
    yield m.eval(
        S.test(
            S.progn(
                S.translatePredicate(S["is"](V.x, 2)),
                S.translatePredicate(plus(V.x, 40, V.z)),
                V.z,
            ),
            42,
        )
    )
