"""The Python twin of examples/libraries/patrick_iterate_quad.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 35565297


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_patrick))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_patrick"])))

    # (= (quad-step $dummy ($t $i $sum))
    #    (if (== $i $t)
    #        ( (+ $t 1) 1 (+ $sum (* $t $i)) )
    #        ( $t (+ $i 1) (+ $sum (* $t $i)) )))
    m += expr(
        S["="],
        expr(S["quad-step"], V["dummy"], expr(V["t"], V["i"], V["sum"])),
        expr(
            S["if"],
            expr(S["=="], V["i"], V["t"]),
            expr(expr(S["+"], V["t"], 1), 1, expr(S["+"], V["sum"], expr(S["*"], V["t"], V["i"]))),
            expr(
                V["t"],
                expr(S["+"], V["i"], 1),
                expr(S["+"], V["sum"], expr(S["*"], V["t"], V["i"])),
            ),
        ),
    )

    # (= (quad-sum $n)
    #    (last (iterate 0 (/ (* $n (+ $n 1)) 2) (1 1 0) quad-step)))
    m += expr(
        S["="],
        expr(S["quad-sum"], V["n"]),
        expr(
            S["last"],
            expr(
                S["iterate"],
                0,
                expr(S["/"], expr(S["*"], V["n"], expr(S["+"], V["n"], 1)), 2),
                expr(1, 1, 0),
                S["quad-step"],
            ),
        ),
    )

    # !(test (quad-sum 1000) 125417041750)
    yield m.eval(expr(S["test"], expr(S["quad-sum"], 1000), 125417041750))

    yield from ()
