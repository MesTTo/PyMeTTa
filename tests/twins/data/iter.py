"""The Python twin of examples/data/iter.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3922


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (make-nat-iter) 0)
    m += expr(S["="], expr(S["make-nat-iter"]), 0)

    # (= (iter-next $N)
    #    (let* (($X $N)
    #           ($Next (+ $N 1)))
    #          ($X $Next)))
    m += expr(
        S["="],
        expr(S["iter-next"], V["N"]),
        expr(
            S["let*"],
            expr(expr(V["X"], V["N"]), expr(V["Next"], expr(S["+"], V["N"], 1))),
            expr(V["X"], V["Next"]),
        ),
    )

    # !(test (let* (($it (make-nat-iter))
    #               (($x1 $it1) (iter-next $it))
    #               (($x2 $it2) (iter-next $it1))
    #               (($x3 $it3) (iter-next $it2)))
    #              ($x1 $x2 $x3))
    #        (0 1 2))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let*"],
                expr(
                    expr(V["it"], expr(S["make-nat-iter"])),
                    expr(expr(V["x1"], V["it1"]), expr(S["iter-next"], V["it"])),
                    expr(expr(V["x2"], V["it2"]), expr(S["iter-next"], V["it1"])),
                    expr(expr(V["x3"], V["it3"]), expr(S["iter-next"], V["it2"])),
                ),
                expr(V["x1"], V["x2"], V["x3"]),
            ),
            expr(0, 1, 2),
        )
    )

    yield from ()
