"""The Python twin of examples/data/test_alpha_unique_atom.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 15730


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (=alpha (alpha-unique-atom ((link $x human) (link $y human) (link $z human)))
    #                ((link $a human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["link"], V["x"], S["human"]),
                        expr(S["link"], V["y"], S["human"]),
                        expr(S["link"], V["z"], S["human"]),
                    ),
                ),
                expr(expr(S["link"], V["a"], S["human"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((parent $x human) (parent $y human) (child $z human)))
    #                ((parent $a human) (child $b human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["parent"], V["x"], S["human"]),
                        expr(S["parent"], V["y"], S["human"]),
                        expr(S["child"], V["z"], S["human"]),
                    ),
                ),
                expr(expr(S["parent"], V["a"], S["human"]), expr(S["child"], V["b"], S["human"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((parent $x human) (child $y human) (friend $z human)))
    #                ((parent $a human) (child $b human) (friend $c human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["parent"], V["x"], S["human"]),
                        expr(S["child"], V["y"], S["human"]),
                        expr(S["friend"], V["z"], S["human"]),
                    ),
                ),
                expr(
                    expr(S["parent"], V["a"], S["human"]),
                    expr(S["child"], V["b"], S["human"]),
                    expr(S["friend"], V["c"], S["human"]),
                ),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((likes $x) (hates $y) (knows $z)))
    #                ((likes $a) (hates $b) (knows $c)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["likes"], V["x"]), expr(S["hates"], V["y"]), expr(S["knows"], V["z"])
                    ),
                ),
                expr(expr(S["likes"], V["a"]), expr(S["hates"], V["b"]), expr(S["knows"], V["c"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((link (foo $x) human) (link (foo $y) human) (link (bar $z) human)))
    #                ((link (foo $a) human) (link (bar $b) human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["link"], expr(S["foo"], V["x"]), S["human"]),
                        expr(S["link"], expr(S["foo"], V["y"]), S["human"]),
                        expr(S["link"], expr(S["bar"], V["z"]), S["human"]),
                    ),
                ),
                expr(
                    expr(S["link"], expr(S["foo"], V["a"]), S["human"]),
                    expr(S["link"], expr(S["bar"], V["b"]), S["human"]),
                ),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((parent (child $x) human) (parent (child $y) human) (parent (child $x) human)))
    #                ((parent (child $a) human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["parent"], expr(S["child"], V["x"]), S["human"]),
                        expr(S["parent"], expr(S["child"], V["y"]), S["human"]),
                        expr(S["parent"], expr(S["child"], V["x"]), S["human"]),
                    ),
                ),
                expr(expr(S["parent"], expr(S["child"], V["a"]), S["human"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((link $x human) (parent $x human) (link $y human) (parent $z human) (link $x human)))
    #                ((link $a human) (parent $a human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["link"], V["x"], S["human"]),
                        expr(S["parent"], V["x"], S["human"]),
                        expr(S["link"], V["y"], S["human"]),
                        expr(S["parent"], V["z"], S["human"]),
                        expr(S["link"], V["x"], S["human"]),
                    ),
                ),
                expr(expr(S["link"], V["a"], S["human"]), expr(S["parent"], V["a"], S["human"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((foo $x) (foo $y) (bar $x) (foo $x) (bar $y)))
    #                ((foo $a) (bar $a)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(
                        expr(S["foo"], V["x"]),
                        expr(S["foo"], V["y"]),
                        expr(S["bar"], V["x"]),
                        expr(S["foo"], V["x"]),
                        expr(S["bar"], V["y"]),
                    ),
                ),
                expr(expr(S["foo"], V["a"]), expr(S["bar"], V["a"])),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom (1 2 2 3 1 4 4 5))
    #                (1 2 3 4 5))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(S["alpha-unique-atom"], expr(1, 2, 2, 3, 1, 4, 4, 5)),
                expr(1, 2, 3, 4, 5),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom (a b a c b d e a))
    #                (a b c d e))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(
                    S["alpha-unique-atom"],
                    expr(S["a"], S["b"], S["a"], S["c"], S["b"], S["d"], S["e"], S["a"]),
                ),
                expr(S["a"], S["b"], S["c"], S["d"], S["e"]),
            ),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ())
    #                ())
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["alpha-unique-atom"], expr()), expr()),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom (1))
    #                (1))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(S["=alpha"], expr(S["alpha-unique-atom"], expr(1)), expr(1)),
            val(value=True),
        )
    )

    # !(test (=alpha (alpha-unique-atom ((link $x human)))
    #                ((link $a human)))
    #        True)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["=alpha"],
                expr(S["alpha-unique-atom"], expr(expr(S["link"], V["x"], S["human"]))),
                expr(expr(S["link"], V["a"], S["human"])),
            ),
            val(value=True),
        )
    )

    yield from ()
