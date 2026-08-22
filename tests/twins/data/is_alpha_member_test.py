"""The Python twin of examples/data/is_alpha_member_test.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 16069


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (is-alpha-member x ()) false)
    yield m.eval(expr(S["test"], expr(S["is-alpha-member"], S["x"], expr()), val(value=False)))

    # !(test (is-alpha-member $x (a b c)) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], V["x"], expr(S["a"], S["b"], S["c"])),
            val(value=False),
        )
    )

    # !(test (is-alpha-member a (a b c)) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], S["a"], expr(S["a"], S["b"], S["c"])),
            val(value=True),
        )
    )

    # !(test (is-alpha-member d (a b c)) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], S["d"], expr(S["a"], S["b"], S["c"])),
            val(value=False),
        )
    )

    # !(test (is-alpha-member (f $x) ((f $y) (g $z)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], V["x"]),
                expr(expr(S["f"], V["y"]), expr(S["g"], V["z"])),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f $x) ((f $y) (f $y)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], V["x"]),
                expr(expr(S["f"], V["y"]), expr(S["f"], V["y"])),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f (g $x) $y) ((f (g $a) $b) (h $c $d)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], expr(S["g"], V["x"]), V["y"]),
                expr(expr(S["f"], expr(S["g"], V["a"]), V["b"]), expr(S["h"], V["c"], V["d"])),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f (g $x) $x) ((f (g $a) $b) (f (g $c) $c)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], expr(S["g"], V["x"]), V["x"]),
                expr(
                    expr(S["f"], expr(S["g"], V["a"]), V["b"]),
                    expr(S["f"], expr(S["g"], V["c"]), V["c"]),
                ),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f $x) ((f $x $y) (g $z)) ) false)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], V["x"]),
                expr(expr(S["f"], V["x"], V["y"]), expr(S["g"], V["z"])),
            ),
            val(value=False),
        )
    )

    # !(test (is-alpha-member 42 (1 2 42 3) ) true)
    yield m.eval(
        expr(S["test"], expr(S["is-alpha-member"], 42, expr(1, 2, 42, 3)), val(value=True))
    )

    # !(test (is-alpha-member 99 (1 2 42 3) ) false)
    yield m.eval(
        expr(S["test"], expr(S["is-alpha-member"], 99, expr(1, 2, 42, 3)), val(value=False))
    )

    # !(test (is-alpha-member (1 $x) ((1 2) (3 4)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], expr(1, V["x"]), expr(expr(1, 2), expr(3, 4))),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (1 $x) ((2 3) (4 5)) ) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], expr(1, V["x"]), expr(expr(2, 3), expr(4, 5))),
            val(value=False),
        )
    )

    # !(test (is-alpha-member a (a b a c)) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], S["a"], expr(S["a"], S["b"], S["a"], S["c"])),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f $x $y) ((f $a $b) (f $c $d)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], V["x"], V["y"]),
                expr(expr(S["f"], V["a"], V["b"]), expr(S["f"], V["c"], V["d"])),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member a (a)) true)
    yield m.eval(expr(S["test"], expr(S["is-alpha-member"], S["a"], expr(S["a"])), val(value=True)))

    # !(test (is-alpha-member b (a)) false)
    yield m.eval(
        expr(S["test"], expr(S["is-alpha-member"], S["b"], expr(S["a"])), val(value=False))
    )

    # !(test (is-alpha-member $x ($y $z $w)) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], V["x"], expr(V["y"], V["z"], V["w"])),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (a (b (c $x))) ((a (b (c $d))) (e $f)) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["a"], expr(S["b"], expr(S["c"], V["x"]))),
                expr(expr(S["a"], expr(S["b"], expr(S["c"], V["d"]))), expr(S["e"], V["f"])),
            ),
            val(value=True),
        )
    )

    # !(test (is-alpha-member (f $x) ((g $y) (h $z)) ) false)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["is-alpha-member"],
                expr(S["f"], V["x"]),
                expr(expr(S["g"], V["y"]), expr(S["h"], V["z"])),
            ),
            val(value=False),
        )
    )

    # !(test (is-alpha-member () (() a b) ) true)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], expr(), expr(expr(), S["a"], S["b"])),
            val(value=True),
        )
    )

    # !(test (is-alpha-member () (a b c) ) false)
    yield m.eval(
        expr(
            S["test"],
            expr(S["is-alpha-member"], expr(), expr(S["a"], S["b"], S["c"])),
            val(value=False),
        )
    )

    # !(let*
    #     (
    #         ($pat (hi name boss))
    #         ($dummy1 (println! (pattern:- $pat)))
    #         ($bool (is-alpha-member $new $pat))
    #         ($dummy2 (println! (is member:- $bool in pattern:- $pat)))
    #     )
    #     ()
    # )
    yield m.eval(
        expr(
            S["let*"],
            expr(
                expr(V["pat"], expr(S["hi"], S["name"], S["boss"])),
                expr(V["dummy1"], expr(S["println!"], expr(S["pattern:-"], V["pat"]))),
                expr(V["bool"], expr(S["is-alpha-member"], V["new"], V["pat"])),
                expr(
                    V["dummy2"],
                    expr(
                        S["println!"],
                        expr(S["is"], S["member:-"], V["bool"], S["in"], S["pattern:-"], V["pat"]),
                    ),
                ),
            ),
            expr(),
        )
    )

    yield from ()
