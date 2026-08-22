"""The Python twin of examples/libraries/he_minimalmetta.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 83244559


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_he))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_he"])))

    # (= (div $x $y $accum)
    #    (chain (eval (- $x $y)) $r1
    #      (chain (eval (< $r1 0)) $r2
    #        (chain (unify $r2 True
    #          $accum
    #          (chain (eval (+ 1 $accum)) $inc
    #            (chain (eval (div $r1 $y $inc)) $r4 $r4)
    #          )) $r3 $r3
    #        )
    #      )
    #    )
    # )
    m += expr(
        S["="],
        expr(S["div"], V["x"], V["y"], V["accum"]),
        expr(
            S["chain"],
            expr(S["eval"], expr(S["-"], V["x"], V["y"])),
            V["r1"],
            expr(
                S["chain"],
                expr(S["eval"], expr(S["<"], V["r1"], 0)),
                V["r2"],
                expr(
                    S["chain"],
                    expr(
                        S["unify"],
                        V["r2"],
                        val(value=True),
                        V["accum"],
                        expr(
                            S["chain"],
                            expr(S["eval"], expr(S["+"], 1, V["accum"])),
                            V["inc"],
                            expr(
                                S["chain"],
                                expr(S["eval"], expr(S["div"], V["r1"], V["y"], V["inc"])),
                                V["r4"],
                                V["r4"],
                            ),
                        ),
                    ),
                    V["r3"],
                    V["r3"],
                ),
            ),
        ),
    )

    # !(test (with-pragma! ((max-stack-depth 1000000))
    #                      (chain (eval (div 350000 5 0)) $rr $rr))
    #        70000)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["with-pragma!"],
                expr(expr(S["max-stack-depth"], 1000000)),
                expr(S["chain"], expr(S["eval"], expr(S["div"], 350000, 5, 0)), V["rr"], V["rr"]),
            ),
            70000,
        )
    )

    yield from ()
