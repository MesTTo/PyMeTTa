"""The Python twin of examples/translation/callquoteevalreduce2.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 10973


def twin(m):
    """Yield one answer group per runnable form, in source order."""
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

    # (= (myfunc)
    #    5)
    m += expr(S["="], expr(S["myfunc"]), 5)

    # (= (call-fib)
    #    (call (fib (myfunc))))
    m += expr(S["="], expr(S["call-fib"]), expr(S["call"], expr(S["fib"], expr(S["myfunc"]))))

    # (= (quote-fib)
    #    (quote (fib (myfunc))))
    m += expr(S["="], expr(S["quote-fib"]), expr(S["quote"], expr(S["fib"], expr(S["myfunc"]))))

    # (= (eval-fib)
    #    (eval (fib (myfunc))))
    m += expr(S["="], expr(S["eval-fib"]), expr(S["eval"], expr(S["fib"], expr(S["myfunc"]))))

    # (= (reduce-fib)
    #    (reduce (fib (myfunc))))
    m += expr(S["="], expr(S["reduce-fib"]), expr(S["reduce"], expr(S["fib"], expr(S["myfunc"]))))

    # !(test (fib-call (call-fib)) (fib-call 5))
    yield m.eval(expr(S["test"], expr(S["fib-call"], expr(S["call-fib"])), expr(S["fib-call"], 5)))

    # !(test (fib-quote (quote-fib)) (fib-quote (quote (fib (myfunc)))))
    yield m.eval(
        expr(
            S["test"],
            expr(S["fib-quote"], expr(S["quote-fib"])),
            expr(S["fib-quote"], expr(S["quote"], expr(S["fib"], expr(S["myfunc"])))),
        )
    )

    # !(test (fib-eval (eval-fib)) (fib-eval 5))
    yield m.eval(expr(S["test"], expr(S["fib-eval"], expr(S["eval-fib"])), expr(S["fib-eval"], 5)))

    # !(test (fib-reduce (reduce-fib)) (fib-reduce 5))
    yield m.eval(
        expr(S["test"], expr(S["fib-reduce"], expr(S["reduce-fib"])), expr(S["fib-reduce"], 5))
    )

    yield from ()
