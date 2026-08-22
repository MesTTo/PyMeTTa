"""The Python twin of examples/reasoning/peano.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 2186406


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

    # (= (expand-once)
    #    (case (match &self (num $t) $t)
    #          (($x (add-atom-no-duplicate &self (num (S $x)))))))
    m += expr(
        S["="],
        expr(S["expand-once"]),
        expr(
            S["case"],
            expr(S["match"], S["&self"], expr(S["num"], V["t"]), V["t"]),
            expr(
                expr(
                    V["x"],
                    expr(
                        S["add-atom-no-duplicate"], S["&self"], expr(S["num"], expr(S["S"], V["x"]))
                    ),
                )
            ),
        ),
    )

    # (= (expandK $n)
    #    (if (== $n 0)
    #        done
    #        (let $temp1 (expand-once)
    #             (expandK (- $n 1)))))
    m += expr(
        S["="],
        expr(S["expandK"], V["n"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            S["done"],
            expr(
                S["let"],
                V["temp1"],
                expr(S["expand-once"]),
                expr(S["expandK"], expr(S["-"], V["n"], 1)),
            ),
        ),
    )

    # (= (demo-peano $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (expandK $K)))
    #          (match &self (num $1) $1)))
    m += expr(
        S["="],
        expr(S["demo-peano"], V["K"]),
        expr(
            S["let*"],
            expr(
                expr(V["s"], expr(S["add-atom"], S["&self"], expr(S["num"], S["Z"]))),
                expr(V["g"], expr(S["expandK"], V["K"])),
            ),
            expr(S["match"], S["&self"], expr(S["num"], V["1"]), V["1"]),
        ),
    )

    # !(test (length (collapse (demo-peano 300))) 301)
    yield m.eval(
        expr(S["test"], expr(S["length"], expr(S["collapse"], expr(S["demo-peano"], 300))), 301)
    )

    yield from ()
