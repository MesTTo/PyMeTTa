"""The Python twin of examples/data/holfunctions.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 14069


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f1a)
    #    (foldl-atom (1 2 3 4) 0 $acc $x (+ $acc $x)))
    m += expr(
        S["="],
        expr(S["f1a"]),
        expr(
            S["foldl-atom"], expr(1, 2, 3, 4), 0, V["acc"], V["x"], expr(S["+"], V["acc"], V["x"])
        ),
    )

    # (= (f2a)
    #    (map-atom (1 2 3) $x (+ $x 1)))
    m += expr(
        S["="], expr(S["f2a"]), expr(S["map-atom"], expr(1, 2, 3), V["x"], expr(S["+"], V["x"], 1))
    )

    # (= (f3a)
    #    (filter-atom (1 2 3 4 5) $x (> $x 3)))
    m += expr(
        S["="],
        expr(S["f3a"]),
        expr(S["filter-atom"], expr(1, 2, 3, 4, 5), V["x"], expr(S[">"], V["x"], 3)),
    )

    # (= (foldfun $a $b) (+ $a $b))
    m += expr(S["="], expr(S["foldfun"], V["a"], V["b"]), expr(S["+"], V["a"], V["b"]))

    # (= (mapfun $a) (+ $a 1))
    m += expr(S["="], expr(S["mapfun"], V["a"]), expr(S["+"], V["a"], 1))

    # (= (filterfun $x) (> $x 3))
    m += expr(S["="], expr(S["filterfun"], V["x"]), expr(S[">"], V["x"], 3))

    # (= (f1b)
    #    (foldl-atom (1 2 3 4) 0 foldfun))
    m += expr(S["="], expr(S["f1b"]), expr(S["foldl-atom"], expr(1, 2, 3, 4), 0, S["foldfun"]))

    # (= (f2b)
    #    (map-atom (1 2 3) mapfun))
    m += expr(S["="], expr(S["f2b"]), expr(S["map-atom"], expr(1, 2, 3), S["mapfun"]))

    # (= (f3b)
    #    (filter-atom (1 2 3 4 5) filterfun))
    m += expr(S["="], expr(S["f3b"]), expr(S["filter-atom"], expr(1, 2, 3, 4, 5), S["filterfun"]))

    # !(test (f1a) 10)
    yield m.eval(expr(S["test"], expr(S["f1a"]), 10))

    # !(test (f2a) (2 3 4))
    yield m.eval(expr(S["test"], expr(S["f2a"]), expr(2, 3, 4)))

    # !(test (f3a) (4 5))
    yield m.eval(expr(S["test"], expr(S["f3a"]), expr(4, 5)))

    # !(test (f1b) 10)
    yield m.eval(expr(S["test"], expr(S["f1b"]), 10))

    # !(test (f2b) (2 3 4))
    yield m.eval(expr(S["test"], expr(S["f2b"]), expr(2, 3, 4)))

    # !(test (f3b) (4 5))
    yield m.eval(expr(S["test"], expr(S["f3b"]), expr(4, 5)))

    # (= (foldfun2 $a $b) (append $a $b))
    m += expr(S["="], expr(S["foldfun2"], V["a"], V["b"]), expr(S["append"], V["a"], V["b"]))

    # !(foldl-atom ((1 2) (3 4) (5 6)) () $acc $x (append $acc $x))
    yield m.eval(
        expr(
            S["foldl-atom"],
            expr(expr(1, 2), expr(3, 4), expr(5, 6)),
            expr(),
            V["acc"],
            V["x"],
            expr(S["append"], V["acc"], V["x"]),
        )
    )

    yield from ()
