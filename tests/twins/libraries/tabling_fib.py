"""The Python twin of examples/libraries/tabling_fib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 81531


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_tabling))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_tabling"])))

    # (= (fib $N)
    #    (if (< $N 2)
    #        $N
    #        (+ (fib (- $N 1))
    #           (fib (- $N 2)))))
    m += expr(
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
    )

    # !(tabled (fib $N))
    yield m.eval(expr(S["tabled"], expr(S["fib"], V["N"])))

    # !(test (fib 30) 832040)
    yield m.eval(expr(S["test"], expr(S["fib"], 30), 832040))

    yield from ()
