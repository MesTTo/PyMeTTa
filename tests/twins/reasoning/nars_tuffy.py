"""The Python twin of examples/reasoning/nars_tuffy.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 16271945


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_nars))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_nars"])))

    # (= (kb)
    #    ((Sentence ((==> (--> (multiplication-sign $1 $2) friend)
    #                     (==> (--> $1 ([] smokes))
    #                          (--> $2 ([] smokes))))
    #                (stv 0.4 0.9)) (1))
    #     (Sentence ((==> (--> $1 ([] smokes))
    #                     (--> $1 ([] cancerous)))
    #                (stv 0.6 0.9)) (2))
    #     (Sentence ((--> (multiplication-sign Anna Bob) friend)
    #                (stv 1.0 0.9)) (3))
    #     (Sentence ((--> (multiplication-sign Anna Edward) friend)
    #                (stv 1.0 0.9)) (4))
    #     (Sentence ((--> (multiplication-sign Anna Frank) friend)
    #                (stv 1.0 0.9)) (5))
    #     (Sentence ((--> (multiplication-sign Edward Frank) friend)
    #                (stv 1.0 0.9)) (6))
    #     (Sentence ((--> (multiplication-sign Gary Helen) friend)
    #                (stv 1.0 0.9)) (7))
    #     (Sentence ((--> (multiplication-sign Gary Frank) friend)
    #                (stv 0.0 0.9)) (8))
    #     (Sentence ((--> Anna ([] smokes))
    #                (stv 1.0 0.9)) (9))
    #     (Sentence ((--> Edward ([] smokes))
    #                (stv 1.0 0.9)) (10))))
    m += expr(
        S["="],
        expr(S["kb"]),
        expr(
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["==>"],
                        expr(
                            S["-->"],
                            expr(S["\N{MULTIPLICATION SIGN}"], V["1"], V["2"]),
                            S["friend"],
                        ),
                        expr(
                            S["==>"],
                            expr(S["-->"], V["1"], expr(S["[]"], S["smokes"])),
                            expr(S["-->"], V["2"], expr(S["[]"], S["smokes"])),
                        ),
                    ),
                    expr(S["stv"], 0.4, 0.9),
                ),
                expr(1),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["==>"],
                        expr(S["-->"], V["1"], expr(S["[]"], S["smokes"])),
                        expr(S["-->"], V["1"], expr(S["[]"], S["cancerous"])),
                    ),
                    expr(S["stv"], 0.6, 0.9),
                ),
                expr(2),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Anna"], S["Bob"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(3),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Anna"], S["Edward"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(4),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Anna"], S["Frank"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(5),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Edward"], S["Frank"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(6),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Gary"], S["Helen"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(7),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(
                        S["-->"],
                        expr(S["\N{MULTIPLICATION SIGN}"], S["Gary"], S["Frank"]),
                        S["friend"],
                    ),
                    expr(S["stv"], 0.0, 0.9),
                ),
                expr(8),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(S["-->"], S["Anna"], expr(S["[]"], S["smokes"])), expr(S["stv"], 1.0, 0.9)
                ),
                expr(9),
            ),
            expr(
                S["Sentence"],
                expr(
                    expr(S["-->"], S["Edward"], expr(S["[]"], S["smokes"])),
                    expr(S["stv"], 1.0, 0.9),
                ),
                expr(10),
            ),
        ),
    )

    # !(test (NARS.Query (kb)
    #                    (--> Edward ([] cancerous)))
    #        ((stv 0.6 0.48941156079382964) (2 5 6 9 10)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["NARS.Query"],
                expr(S["kb"]),
                expr(S["-->"], S["Edward"], expr(S["[]"], S["cancerous"])),
            ),
            expr(expr(S["stv"], 0.6, 0.48941156079382964), expr(2, 5, 6, 9, 10)),
        )
    )

    yield from ()
