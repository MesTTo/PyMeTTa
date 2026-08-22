"""The Python twin of examples/translation/translatorrule_fib.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6199


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (fib-tr $n $a $b)
    #    (if (== $n 0)
    #        $a
    #        (fib-tr (- $n 1) $b (+ $a $b))))
    m += expr(
        S["="],
        expr(S["fib-tr"], V["n"], V["a"], V["b"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            V["a"],
            expr(S["fib-tr"], expr(S["-"], V["n"], 1), V["b"], expr(S["+"], V["a"], V["b"])),
        ),
    )

    # (= (fib $n)
    #    (fib-tr $n 0 1))
    m += expr(S["="], expr(S["fib"], V["n"]), expr(S["fib-tr"], V["n"], 0, 1))

    # (= (compilefib $n)
    #    (fib $n))
    m += expr(S["="], expr(S["compilefib"], V["n"]), expr(S["fib"], V["n"]))

    # !(add-translator-rule! compilefib)
    yield m.eval(expr(S["add-translator-rule!"], S["compilefib"]))

    # (= (smartfun $b)
    #    (* (compilefib 10) $b))
    m += expr(S["="], expr(S["smartfun"], V["b"]), expr(S["*"], expr(S["compilefib"], 10), V["b"]))

    # !(test (smartfun 42) 2310)
    yield m.eval(expr(S["test"], expr(S["smartfun"], 42), 2310))

    yield from ()
