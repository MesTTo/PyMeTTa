"""The Python twin of examples/functions/curry.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 12763


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f $a $b) (+ $a $b))
    m += expr(S["="], expr(S["f"], V["a"], V["b"]), expr(S["+"], V["a"], V["b"]))

    # (= (g $a $b $c) (+ $c (+ $a $b)))
    m += expr(
        S["="],
        expr(S["g"], V["a"], V["b"], V["c"]),
        expr(S["+"], V["c"], expr(S["+"], V["a"], V["b"])),
    )

    # (= (show) (repr (f 1)))
    m += expr(S["="], expr(S["show"]), expr(S["repr"], expr(S["f"], 1)))

    # !(test (repr (f 1)) "(partial f (1))")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["f"], 1)), val("(partial f (1))")))

    # !(test ((f 1) 2) 3)
    yield m.eval(expr(S["test"], expr(expr(S["f"], 1), 2), 3))

    # !(test (repr (g 1 2)) "(partial g (1 2))")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["g"], 1, 2)), val("(partial g (1 2))")))

    # (= (h $A $B)
    #    (append ($A) $B))
    m += expr(S["="], expr(S["h"], V["A"], V["B"]), expr(S["append"], expr(V["A"]), V["B"]))

    # !(test ((h 42) (1 2 3)) (42 1 2 3))
    yield m.eval(expr(S["test"], expr(expr(S["h"], 42), expr(1, 2, 3)), expr(42, 1, 2, 3)))

    # !(test (repr (h 42)) "(partial h (42))")
    yield m.eval(expr(S["test"], expr(S["repr"], expr(S["h"], 42)), val("(partial h (42))")))

    # !(test (map-atom (1 2 3) (+ 1)) (2 3 4))
    yield m.eval(
        expr(S["test"], expr(S["map-atom"], expr(1, 2, 3), expr(S["+"], 1)), expr(2, 3, 4))
    )

    # !(test (+ 1 2 3) (Error (+ 1 2 3) IncorrectNumberOfArguments))
    yield m.eval(
        expr(
            S["test"],
            expr(S["+"], 1, 2, 3),
            expr(S["Error"], expr(S["+"], 1, 2, 3), S["IncorrectNumberOfArguments"]),
        )
    )

    # !(test (reduce (+ 1 2 3)) (Error (+ 1 2 3) IncorrectNumberOfArguments))
    yield m.eval(
        expr(
            S["test"],
            expr(S["reduce"], expr(S["+"], 1, 2, 3)),
            expr(S["Error"], expr(S["+"], 1, 2, 3), S["IncorrectNumberOfArguments"]),
        )
    )

    # !(test (empty 1 2) (empty 1 2))
    yield m.eval(expr(S["test"], expr(S["empty"], 1, 2), expr(S["empty"], 1, 2)))

    # (= (overloaded-curry $a) $a)
    m += expr(S["="], expr(S["overloaded-curry"], V["a"]), V["a"])

    # (= (overloaded-curry $a $b $c) (+ $a (+ $b $c)))
    m += expr(
        S["="],
        expr(S["overloaded-curry"], V["a"], V["b"], V["c"]),
        expr(S["+"], V["a"], expr(S["+"], V["b"], V["c"])),
    )

    # !(test (repr (overloaded-curry 1 2)) "(partial overloaded-curry (1 2))")
    yield m.eval(
        expr(
            S["test"],
            expr(S["repr"], expr(S["overloaded-curry"], 1, 2)),
            val("(partial overloaded-curry (1 2))"),
        )
    )

    yield from ()
