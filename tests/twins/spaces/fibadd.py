"""The Python twin of examples/spaces/fibadd.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 28277895


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &self (= (fib $N)
    #                     (if (< $N 2)
    #                         $N
    #                         (+ (fib (- $N 1))
    #                            (fib (- $N 2))))))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&self"],
            expr(
                S["="],
                expr(S["fib"], V["N"]),
                expr(
                    S["if"],
                    expr(S["<"], V["N"], 2),
                    V["N"],
                    expr(
                        S["+"],
                        expr(S["fib"], expr(S["-"], V["N"], 1)),
                        expr(S["fib"], expr(S["-"], V["N"], 2)),
                    ),
                ),
            ),
        )
    )

    # !(test (with-pragma! ((max-stack-depth 100000000)) (fib 30)) 832040)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"], expr(expr(S["max-stack-depth"], 100000000)), expr(S["fib"], 30)
            ),
            832040,
        )
    )

    yield from ()
