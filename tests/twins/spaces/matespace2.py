"""The Python twin of examples/spaces/matespace2.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 39336332


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    m += expr(
        S["="],
        expr(S["add-atom-no-duplicate"], V["Space"], V["Atom"]),
        expr(
            S["if"],
            expr(
                S["=="],
                expr(),
                expr(
                    S["collapse"],
                    expr(S["once"], expr(S["match"], V["Space"], V["Atom"], V["Atom"])),
                ),
            ),
            expr(S["add-atom"], V["Space"], V["Atom"]),
            expr(S["empty"]),
        ),
    )

    # (= (expand)
    #    (case (superpose (collapse (match &self (num $t) $t)))
    #          (($t ((add-atom-no-duplicate &self (num (M $t)))
    #                (add-atom-no-duplicate &self (num (W $t))))))))
    m += expr(
        S["="],
        expr(S["expand"]),
        expr(
            S["case"],
            expr(
                S["superpose"],
                expr(S["collapse"], expr(S["match"], S["&self"], expr(S["num"], V["t"]), V["t"])),
            ),
            expr(
                expr(
                    V["t"],
                    expr(
                        expr(
                            S["add-atom-no-duplicate"],
                            S["&self"],
                            expr(S["num"], expr(S["M"], V["t"])),
                        ),
                        expr(
                            S["add-atom-no-duplicate"],
                            S["&self"],
                            expr(S["num"], expr(S["W"], V["t"])),
                        ),
                    ),
                )
            ),
        ),
    )

    # (= (mate)
    #    (case (superpose (collapse (match &self (num (M $t)) $t)))
    #          (($t (case (once (match &self (num (W $t)) $t))
    #                     (($t (add-atom-no-duplicate &self (num (C $t))))))))))
    m += expr(
        S["="],
        expr(S["mate"]),
        expr(
            S["case"],
            expr(
                S["superpose"],
                expr(
                    S["collapse"],
                    expr(S["match"], S["&self"], expr(S["num"], expr(S["M"], V["t"])), V["t"]),
                ),
            ),
            expr(
                expr(
                    V["t"],
                    expr(
                        S["case"],
                        expr(
                            S["once"],
                            expr(
                                S["match"], S["&self"], expr(S["num"], expr(S["W"], V["t"])), V["t"]
                            ),
                        ),
                        expr(
                            expr(
                                V["t"],
                                expr(
                                    S["add-atom-no-duplicate"],
                                    S["&self"],
                                    expr(S["num"], expr(S["C"], V["t"])),
                                ),
                            )
                        ),
                    ),
                )
            ),
        ),
    )

    # (= (rewriteK $n)
    #    (if (== $n 0)
    #        done
    #        (let* (($temp1 (expand))
    #               ($temp2 (mate)))
    #              (rewriteK (- $n 1)))))
    m += expr(
        S["="],
        expr(S["rewriteK"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            S["done"],
            expr(
                S["let*"],
                expr(expr(V["temp1"], expr(S["expand"])), expr(V["temp2"], expr(S["mate"]))),
                expr(S["rewriteK"], expr(S["-"], V["n"], 1)),
            ),
        ),
    )

    # (= (mate-space-demo $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (rewriteK $K)))
    #           (match &self (num $1) (num $1))))
    m += expr(
        S["="],
        expr(S["mate-space-demo"], V["K"]),
        expr(
            S["let*"],
            expr(
                expr(V["s"], expr(S["add-atom"], S["&self"], expr(S["num"], S["Z"]))),
                expr(V["g"], expr(S["rewriteK"], V["K"])),
            ),
            expr(S["match"], S["&self"], expr(S["num"], V["1"]), expr(S["num"], V["1"])),
        ),
    )

    # !(test (length (collapse (mate-space-demo 80))) 1297533)
    yield m.eval(
        expr(
            S["test"],
            expr(S["length"], expr(S["collapse"], expr(S["mate-space-demo"], 80))),
            1297533,
        )
    )

    yield from ()
