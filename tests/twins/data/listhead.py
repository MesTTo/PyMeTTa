"""The Python twin of examples/data/listhead.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4655


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (len ()) 0)
    m += expr(S["="], expr(S["len"], expr()), 0)

    # (= (len (cons $Head $Tail))
    #    (let $N0 (len $Tail)
    #         (+ $N0 1)))
    m += expr(
        S["="],
        expr(S["len"], expr(S["cons"], V["Head"], V["Tail"])),
        expr(S["let"], V["N0"], expr(S["len"], V["Tail"]), expr(S["+"], V["N0"], 1)),
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

    # !(test (len (1 2 3)) 3)
    yield m.eval(expr(S["test"], expr(S["len"], expr(1, 2, 3)), 3))

    # !(test (cons 42 ()) (42))
    yield m.eval(expr(S["test"], expr(S["cons"], 42, expr()), expr(42)))

    yield from ()
