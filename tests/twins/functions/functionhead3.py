"""The Python twin of examples/functions/functionhead3.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 9283


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (in $x $L)
    #    (let True (is-member $x $L) $x))
    m += expr(
        S["="],
        expr(S["in"], V["x"], V["L"]),
        expr(S["let"], val(value=True), expr(S["is-member"], V["x"], V["L"]), V["x"]),
    )

    # (= (myplus $A $B)
    #    (let $A (in $X (1 2 3))
    #      (let $B (in $Y (2 3))
    #        (in (+ $X $Y) (3 4 5)))))
    m += expr(
        S["="],
        expr(S["myplus"], V["A"], V["B"]),
        expr(
            S["let"],
            V["A"],
            expr(S["in"], V["X"], expr(1, 2, 3)),
            expr(
                S["let"],
                V["B"],
                expr(S["in"], V["Y"], expr(2, 3)),
                expr(S["in"], expr(S["+"], V["X"], V["Y"]), expr(3, 4, 5)),
            ),
        ),
    )

    # !(test (collapse (myplus 1 3)) (4))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["myplus"], 1, 3)), expr(4)))

    # !(test (collapse (myplus 3 3)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["myplus"], 3, 3)), expr()))

    # !(test (collapse (myplus 3 4)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["myplus"], 3, 4)), expr()))

    # !(test (collapse (myplus $x 3)) (4 5))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["myplus"], V["x"], 3)), expr(4, 5)))

    # !(test (collapse (myplus $x $y)) (3 4 4 5 5))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["myplus"], V["x"], V["y"])), expr(3, 4, 4, 5, 5))
    )

    # !(test (collapse (let True (> (myplus $x 2) 3) $x)) (2 3))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["let"], val(value=True), expr(S[">"], expr(S["myplus"], V["x"], 2), 3), V["x"]
                ),
            ),
            expr(2, 3),
        )
    )

    yield from ()
