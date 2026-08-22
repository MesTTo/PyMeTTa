"""The Python twin of examples/translation/translatepredicate.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 685


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (progn (translatePredicate (is $x 2))
    #               (translatePredicate (+ $x 40 $z)) $z)
    #        42)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["progn"],
                expr(S["translatePredicate"], expr(S["is"], V["x"], 2)),
                expr(S["translatePredicate"], expr(S["+"], V["x"], 40, V["z"])),
                V["z"],
            ),
            42,
        )
    )

    yield from ()
