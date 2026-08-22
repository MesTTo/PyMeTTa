"""The Python twin of examples/performance/peanofast.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 66870


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (expandK $expression $n)
    #    (if (== $n 0)
    #        done
    #        (let $temp1 (add-atom &self (num $expression))
    #             (expandK (S $expression) (- $n 1)))))
    m += expr(
        S["="],
        expr(S["expandK"], V["expression"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            S["done"],
            expr(
                S["let"],
                V["temp1"],
                expr(S["add-atom"], S["&self"], expr(S["num"], V["expression"])),
                expr(S["expandK"], expr(S["S"], V["expression"]), expr(S["-"], V["n"], 1)),
            ),
        ),
    )

    # (= (demo-peano $K)
    #    (expandK Z $K))
    m += expr(S["="], expr(S["demo-peano"], V["K"]), expr(S["expandK"], S["Z"], V["K"]))

    # !(demo-peano 2500)
    yield m.eval(expr(S["demo-peano"], 2500))

    # !(test (length (collapse (match &self (num $1) $1))) 2500)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["length"],
                expr(S["collapse"], expr(S["match"], S["&self"], expr(S["num"], V["1"]), V["1"])),
            ),
            2500,
        )
    )

    yield from ()
