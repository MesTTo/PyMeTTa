"""The Python twin of examples/libraries/roman_test.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 212336


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(import! &self (library lib_roman))
    yield m.eval(expr(S["import!"], S["&self"], expr(S["library"], S["lib_roman"])))

    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(
        expr(S["test"], expr(S["map-flat"], expr(S["+"], 1), expr(1, 2, 3)), expr(2, 3, 4))
    )

    # !(test (map-nested (+ 1) (1 (2 3))) (2 (3 4)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["map-nested"], expr(S["+"], 1), expr(1, expr(2, 3))),
            expr(2, expr(3, 4)),
        )
    )

    # !(test (fold-flat + 0 (1 2 3)) 6)
    yield m.eval(expr(S["test"], expr(S["fold-flat"], S["+"], 0, expr(1, 2, 3)), 6))

    # !(test (foldr-flat cons () (1 (2 3) 4)) (1 (2 3) 4))
    yield m.eval(
        expr(
            S["test"],
            expr(S["foldr-flat"], S["cons"], expr(), expr(1, expr(2, 3), 4)),
            expr(1, expr(2, 3), 4),
        )
    )

    # !(test (fold-nested + 0 (1 (2 3))) 6)
    yield m.eval(expr(S["test"], expr(S["fold-nested"], S["+"], 0, expr(1, expr(2, 3))), 6))

    # !(test (/=\ (1 2 $a) (2 3 4)) (2 2))
    yield m.eval(expr(S["test"], expr(S["/=\\"], expr(1, 2, V["a"]), expr(2, 3, 4)), expr(2, 2)))

    # !(test (/==\ (1 2 3) (2 3 4)) (2 3))
    yield m.eval(expr(S["test"], expr(S["/==\\"], expr(1, 2, 3), expr(2, 3, 4)), expr(2, 3)))

    # !(test (/=a\ (1 2 $a) (2 $a 4)) (2 $a))
    yield m.eval(
        expr(S["test"], expr(S["/=a\\"], expr(1, 2, V["a"]), expr(2, V["a"], 4)), expr(2, V["a"]))
    )

    # !(test (\= (1 2 3) ($a 3 4)) (2))
    yield m.eval(expr(S["test"], expr(S["\\="], expr(1, 2, 3), expr(V["a"], 3, 4)), expr(2)))

    # !(test (\== (1 2 3) (2 3 4)) (1))
    yield m.eval(expr(S["test"], expr(S["\\=="], expr(1, 2, 3), expr(2, 3, 4)), expr(1)))

    # !(test (\=a (1 2 $a) (2 $a 4)) (1))
    yield m.eval(expr(S["test"], expr(S["\\=a"], expr(1, 2, V["a"]), expr(2, V["a"], 4)), expr(1)))

    # !(test (\=/ (1 2 3) ($a 3 4)) (2 1 3 4))
    yield m.eval(
        expr(S["test"], expr(S["\\=/"], expr(1, 2, 3), expr(V["a"], 3, 4)), expr(2, 1, 3, 4))
    )

    # !(test (\==/ (1 2 3) (2 3 4)) (1 2 3 4))
    yield m.eval(expr(S["test"], expr(S["\\==/"], expr(1, 2, 3), expr(2, 3, 4)), expr(1, 2, 3, 4)))

    # !(test (\=a/ (1 2 $a) (2 $a 4)) (1 2 $a 4))
    yield m.eval(
        expr(
            S["test"],
            expr(S["\\=a/"], expr(1, 2, V["a"]), expr(2, V["a"], 4)),
            expr(1, 2, V["a"], 4),
        )
    )

    # !(test (. (+ 1) (* 2) 1) 3)
    yield m.eval(expr(S["test"], expr(S["."], expr(S["+"], 1), expr(S["*"], 2), 1), 3))

    # !(test (.: (+ 1) + 2 3) 6)
    yield m.eval(expr(S["test"], expr(S[".:"], expr(S["+"], 1), S["+"], 2, 3), 6))

    # !(test (&&& (+ 2) (* 2) 1) (3 2))
    yield m.eval(expr(S["test"], expr(S["&&&"], expr(S["+"], 2), expr(S["*"], 2), 1), expr(3, 2)))

    # (= (mfail $x) (empty))
    m += expr(S["="], expr(S["mfail"], V["x"]), expr(S["empty"]))

    # !(test (collapse (&^& (+ 1) (mfail) 1)) (2))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["&^&"], expr(S["+"], 1), expr(S["mfail"]), 1)),
            expr(2),
        )
    )

    # !(test (let (@ $lst (cons $h $t)) (1 2 3) ($lst $h $t)) ((1 2 3) 1 (2 3)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["let"],
                expr(S["@"], V["lst"], expr(S["cons"], V["h"], V["t"])),
                expr(1, 2, 3),
                expr(V["lst"], V["h"], V["t"]),
            ),
            expr(expr(1, 2, 3), 1, expr(2, 3)),
        )
    )

    # !(test (let (head $x) (1 2 3) $x) 1)
    yield m.eval(expr(S["test"], expr(S["let"], expr(S["head"], V["x"]), expr(1, 2, 3), V["x"]), 1))

    # !(test (let (tail $xs) (1 2 3) $xs) (2 3))
    yield m.eval(
        expr(
            S["test"], expr(S["let"], expr(S["tail"], V["xs"]), expr(1, 2, 3), V["xs"]), expr(2, 3)
        )
    )

    # !(test (let (mylast $x) (1 2 3) $x) 3)
    yield m.eval(
        expr(S["test"], expr(S["let"], expr(S["mylast"], V["x"]), expr(1, 2, 3), V["x"]), 3)
    )

    # !(test (let (init $xs) (1 2 3) $xs) (1 2))
    yield m.eval(
        expr(
            S["test"], expr(S["let"], expr(S["init"], V["xs"]), expr(1, 2, 3), V["xs"]), expr(1, 2)
        )
    )

    # !(test (let (rcons $xs $x) (1 2 3) ($xs $x)) ((1 2) 3))
    yield m.eval(
        expr(
            S["test"],
            expr(S["let"], expr(S["rcons"], V["xs"], V["x"]), expr(1, 2, 3), expr(V["xs"], V["x"])),
            expr(expr(1, 2), 3),
        )
    )

    # !(test (prog1 (+ 1 1) (+ 2 2)) 2)
    yield m.eval(expr(S["test"], expr(S["prog1"], expr(S["+"], 1, 1), expr(S["+"], 2, 2)), 2))

    # !(test (progn (+ 1 1) (+ 2 2)) 4)
    yield m.eval(expr(S["test"], expr(S["progn"], expr(S["+"], 1, 1), expr(S["+"], 2, 2)), 4))

    yield from ()
