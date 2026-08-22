"""The Python twin of examples/functions/invertfunction.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6229


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f $X $Y)
    #    (append ($X) $Y))
    m += expr(S["="], expr(S["f"], V["X"], V["Y"]), expr(S["append"], expr(V["X"]), V["Y"]))

    # (= (g $X $Y $Z)
    #    (append ((#+ $X $Z)) $Y))
    m += expr(
        S["="],
        expr(S["g"], V["X"], V["Y"], V["Z"]),
        expr(S["append"], expr(expr(S["#+"], V["X"], V["Z"])), V["Y"]),
    )

    # !(test (let (cons $Head $Tail) (1 2 3 4 5 6) ($Head $Tail))
    #             (1 (2 3 4 5 6)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                expr(S["cons"], V["Head"], V["Tail"]),
                expr(1, 2, 3, 4, 5, 6),
                expr(V["Head"], V["Tail"]),
            ),
            expr(1, expr(2, 3, 4, 5, 6)),
        )
    )

    # !(test (let (f $Head $Tail) (1 2 3 4 5 6) ($Head $Tail))
    #             (1 (2 3 4 5 6)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                expr(S["f"], V["Head"], V["Tail"]),
                expr(1, 2, 3, 4, 5, 6),
                expr(V["Head"], V["Tail"]),
            ),
            expr(1, expr(2, 3, 4, 5, 6)),
        )
    )

    # !(test (let (g $X $Y 35) (42 2 3)
    #             ($X $Y 40))
    #        (7 (2 3) 40))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"], expr(S["g"], V["X"], V["Y"], 35), expr(42, 2, 3), expr(V["X"], V["Y"], 40)
            ),
            expr(7, expr(2, 3), 40),
        )
    )

    yield from ()
