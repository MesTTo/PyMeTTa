"""The Python twin of examples/functions/functionhead.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6376


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (myfunc $A $B)
    #    (append (append (42) $A) $B))
    m += expr(
        S["="],
        expr(S["myfunc"], V["A"], V["B"]),
        expr(S["append"], expr(S["append"], expr(42), V["A"]), V["B"]),
    )

    # (= (h_old $A $C)
    #    (if (= $A (myfunc (10) $B)) ;= is also unification in PeTTa
    #        ($B $C)
    #        (empty)))
    m += expr(
        S["="],
        expr(S["h_old"], V["A"], V["C"]),
        expr(
            S["if"],
            expr(S["="], V["A"], expr(S["myfunc"], expr(10), V["B"])),
            expr(V["B"], V["C"]),
            expr(S["empty"]),
        ),
    )

    # (= (h $A $C)
    #    (let $A (myfunc (10) $B)
    #         ($B $C)))
    m += expr(
        S["="],
        expr(S["h"], V["A"], V["C"]),
        expr(S["let"], V["A"], expr(S["myfunc"], expr(10), V["B"]), expr(V["B"], V["C"])),
    )

    # !(test (h (42 10 40) 42000)
    #        ((40) 42000))
    yield m.eval(expr(S["test"], expr(S["h"], expr(42, 10, 40), 42000), expr(expr(40), 42000)))

    # !(test (h_old (42 10 40) 42000)
    #        ((40) 42000))
    yield m.eval(expr(S["test"], expr(S["h_old"], expr(42, 10, 40), 42000), expr(expr(40), 42000)))

    yield from ()
