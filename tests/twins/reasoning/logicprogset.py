"""The Python twin of examples/reasoning/logicprogset.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 2948


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (myf $M)
    #    (and (and (member a $M)
    #              (member b $M))
    #         (== (size-atom $M) 2)))
    m += expr(
        S["="],
        expr(S["myf"], V["M"]),
        expr(
            S["and"],
            expr(S["and"], expr(S["member"], S["a"], V["M"]), expr(S["member"], S["b"], V["M"])),
            expr(S["=="], expr(S["size-atom"], V["M"]), 2),
        ),
    )

    # !(test (if (once (myf $M)) $M)
    #        (a b))
    yield m.eval(
        expr(
            S["test"],
            expr(S["if"], expr(S["once"], expr(S["myf"], V["M"])), V["M"]),
            expr(S["a"], S["b"]),
        )
    )

    yield from ()
