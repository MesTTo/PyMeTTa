"""The Python twin of examples/functions/invertpeanoplus.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 12762


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (plus Z $y) $y)
    m += expr(S["="], expr(S["plus"], S["Z"], V["y"]), V["y"])

    # (= (plus (S $x) $y)
    #    (S (plus $x $y)))
    m += expr(
        S["="],
        expr(S["plus"], expr(S["S"], V["x"]), V["y"]),
        expr(S["S"], expr(S["plus"], V["x"], V["y"])),
    )

    # !(test (plus (S (S Z)) (S Z))
    #        (S (S (S Z))))
    yield m.eval(
        expr(
            S["test"],
            expr(S["plus"], expr(S["S"], expr(S["S"], S["Z"])), expr(S["S"], S["Z"])),
            expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))),
        )
    )

    # !(test (let (plus $A (S Z)) (S (S (S (S Z)))) $A)
    #        (S (S (S Z))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                expr(S["plus"], V["A"], expr(S["S"], S["Z"])),
                expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))),
                V["A"],
            ),
            expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))),
        )
    )

    # !(test (let (plus (S Z) $B) (S (S (S (S Z)))) $B)
    #        (S (S (S Z))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                expr(S["plus"], expr(S["S"], S["Z"]), V["B"]),
                expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))),
                V["B"],
            ),
            expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))),
        )
    )

    # !(test (collapse (let (plus $A $B) (S (S (S (S Z)))) ;-> ($A,$B) in {(0,4),(1,3),(2,2),(3,1),(4,0)}
    #                       ($A $B)))
    #        ((Z (S (S (S (S Z)))))
    #        ((S Z) (S (S (S Z))))
    #        ((S (S Z)) (S (S Z)))
    #        ((S (S (S Z))) (S Z))
    #        ((S (S (S (S Z)))) Z)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"],
                    expr(S["plus"], V["A"], V["B"]),
                    expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))),
                    expr(V["A"], V["B"]),
                ),
            ),
            expr(
                expr(S["Z"], expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))))),
                expr(expr(S["S"], S["Z"]), expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))),
                expr(expr(S["S"], expr(S["S"], S["Z"])), expr(S["S"], expr(S["S"], S["Z"]))),
                expr(expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))), expr(S["S"], S["Z"])),
                expr(expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))), S["Z"]),
            ),
        )
    )

    # !(test (once (let (plus $A $B) (S (S (S (S Z))))
    #                   ($A $B)))
    #        (Z (S (S (S (S Z))))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["once"],
                expr(
                    S["let"],
                    expr(S["plus"], V["A"], V["B"]),
                    expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"])))),
                    expr(V["A"], V["B"]),
                ),
            ),
            expr(S["Z"], expr(S["S"], expr(S["S"], expr(S["S"], expr(S["S"], S["Z"]))))),
        )
    )

    yield from ()
