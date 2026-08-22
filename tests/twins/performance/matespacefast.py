"""The Python twin of examples/performance/matespacefast.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 34349629


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (rewriteK $t $n)
    #    (if (== $n 0)
    #        done
    #        (let* (($_1 (add-atom &self (num (M $t))))
    #               ($_2 (add-atom &self (num (W $t))))
    #               ($_3 (add-atom &self (num (C $t)))))
    #              ((rewriteK (M $t) (- $n 1))
    #               (rewriteK (W $t) (- $n 1))))))
    m += expr(
        S["="],
        expr(S["rewriteK"], V["t"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            S["done"],
            expr(
                S["let*"],
                expr(
                    expr(
                        V["_1"],
                        expr(S["add-atom"], S["&self"], expr(S["num"], expr(S["M"], V["t"]))),
                    ),
                    expr(
                        V["_2"],
                        expr(S["add-atom"], S["&self"], expr(S["num"], expr(S["W"], V["t"]))),
                    ),
                    expr(
                        V["_3"],
                        expr(S["add-atom"], S["&self"], expr(S["num"], expr(S["C"], V["t"]))),
                    ),
                ),
                expr(
                    expr(S["rewriteK"], expr(S["M"], V["t"]), expr(S["-"], V["n"], 1)),
                    expr(S["rewriteK"], expr(S["W"], V["t"]), expr(S["-"], V["n"], 1)),
                ),
            ),
        ),
    )

    # (= (mate-space-demo $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (rewriteK Z $K)))
    #           (match &self (num $1) (num $1))))
    m += expr(
        S["="],
        expr(S["mate-space-demo"], V["K"]),
        expr(
            S["let*"],
            expr(
                expr(V["s"], expr(S["add-atom"], S["&self"], expr(S["num"], S["Z"]))),
                expr(V["g"], expr(S["rewriteK"], S["Z"], V["K"])),
            ),
            expr(S["match"], S["&self"], expr(S["num"], V["1"]), expr(S["num"], V["1"])),
        ),
    )

    # !(test (length (collapse (mate-space-demo 19))) 1572862)
    yield m.eval(
        expr(
            S["test"],
            expr(S["length"], expr(S["collapse"], expr(S["mate-space-demo"], 19))),
            1572862,
        )
    )

    yield from ()
