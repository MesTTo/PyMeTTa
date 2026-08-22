"""The Python twin of examples/data/foldall.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 22960


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f) 2)
    m += expr(S["="], expr(S["f"]), 2)

    # (= (f) 3)
    m += expr(S["="], expr(S["f"]), 3)

    # (= (g 1) 2)
    m += expr(S["="], expr(S["g"], 1), 2)

    # (= (g 2) 3)
    m += expr(S["="], expr(S["g"], 2), 3)

    # (= (merge $A $B) (+ $A $B))
    m += expr(S["="], expr(S["merge"], V["A"], V["B"]), expr(S["+"], V["A"], V["B"]))

    # !(test (foldall merge (f) 0)
    #        5)
    yield m.eval(expr(S["test"], expr(S["foldall"], S["merge"], expr(S["f"]), 0), 5))

    # !(test (foldall merge (g $x) 0)
    #        5)
    yield m.eval(expr(S["test"], expr(S["foldall"], S["merge"], expr(S["g"], V["x"]), 0), 5))

    # !(test (let $agglambda (|-> ($x $y) (+ $x $y))
    #             (foldall $agglambda (f) 0))
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["agglambda"],
                expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                expr(S["foldall"], V["agglambda"], expr(S["f"]), 0),
            ),
            5,
        )
    )

    # !(test (let $agglambda (|-> ($x $y) (+ $x $y))
    #             (foldall $agglambda (g $z) 0))
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["agglambda"],
                expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                expr(S["foldall"], V["agglambda"], expr(S["g"], V["z"]), 0),
            ),
            5,
        )
    )

    # !(test (let $agglambda (|-> ($x $y) (+ $x $y))
    #             (foldall $agglambda (g $z) 0))
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                V["agglambda"],
                expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                expr(S["foldall"], V["agglambda"], expr(S["g"], V["z"]), 0),
            ),
            5,
        )
    )

    # !(test (let* (($agglambda (|-> ($x $y) (+ $x $y)))
    #               ($genlambda (|-> ($z) (f))))
    #             (foldall $agglambda ($genlambda $x) 0))
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let*"],
                expr(
                    expr(
                        V["agglambda"],
                        expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                    ),
                    expr(V["genlambda"], expr(S["|->"], expr(V["z"]), expr(S["f"]))),
                ),
                expr(S["foldall"], V["agglambda"], expr(V["genlambda"], V["x"]), 0),
            ),
            5,
        )
    )

    # !(test (let* (($agglambda (|-> ($x $y) (+ $x $y)))
    #               ($genlambda (|-> ($z) (g $z))))
    #             (foldall $agglambda ($genlambda $x) 0))
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let*"],
                expr(
                    expr(
                        V["agglambda"],
                        expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                    ),
                    expr(V["genlambda"], expr(S["|->"], expr(V["z"]), expr(S["g"], V["z"]))),
                ),
                expr(S["foldall"], V["agglambda"], expr(V["genlambda"], V["x"]), 0),
            ),
            5,
        )
    )

    # !(test (foldall (|-> ($x $y) (+ $x $y))
    #                 ((|-> ($z) (g $z)) $w) 0)
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["foldall"],
                expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                expr(expr(S["|->"], expr(V["z"]), expr(S["g"], V["z"])), V["w"]),
                0,
            ),
            5,
        )
    )

    # !(test (foldall (if True (let $f (|-> ($x $y) (+ $x $y)) $f) (empty))
    #                 ((|-> ($z) (g $z)) $w) 0)
    #        5)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["foldall"],
                expr(
                    S["if"],
                    val(value=True),
                    expr(
                        S["let"],
                        V["f"],
                        expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                        V["f"],
                    ),
                    expr(S["empty"]),
                ),
                expr(expr(S["|->"], expr(V["z"]), expr(S["g"], V["z"])), V["w"]),
                0,
            ),
            5,
        )
    )

    # !(test (foldall (if True (let $f (|-> ($x $y) (+ $x $y)) $f) (empty))
    #                 ((|-> ($z) (* 2 (g $z))) $w) 0)
    #        10)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["foldall"],
                expr(
                    S["if"],
                    val(value=True),
                    expr(
                        S["let"],
                        V["f"],
                        expr(S["|->"], expr(V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
                        V["f"],
                    ),
                    expr(S["empty"]),
                ),
                expr(expr(S["|->"], expr(V["z"]), expr(S["*"], 2, expr(S["g"], V["z"]))), V["w"]),
                0,
            ),
            10,
        )
    )

    yield from ()
