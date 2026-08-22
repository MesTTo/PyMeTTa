"""The Python twin of examples/reasoning/logicprog.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr, val

#: Inferences this twin spends, its own tripwire.
BUDGET = 9036


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &petta (dispatch-policy successor NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["successor"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(add-atom &petta (dispatch-policy later-in-alphabet NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["later-in-alphabet"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # (= (successor b a) True)
    m += expr(S["="], expr(S["successor"], S["b"], S["a"]), val(value=True))

    # (= (successor c b) True)
    m += expr(S["="], expr(S["successor"], S["c"], S["b"]), val(value=True))

    # (= (successor d c) True)
    m += expr(S["="], expr(S["successor"], S["d"], S["c"]), val(value=True))

    # (= (successor e d) True)
    m += expr(S["="], expr(S["successor"], S["e"], S["d"]), val(value=True))

    # (= (successor f e) True)
    m += expr(S["="], expr(S["successor"], S["f"], S["e"]), val(value=True))

    # (= (successor g f) True)
    m += expr(S["="], expr(S["successor"], S["g"], S["f"]), val(value=True))

    # (= (later-in-alphabet $X $Y)
    #    (successor $X $Y))
    m += expr(
        S["="], expr(S["later-in-alphabet"], V["X"], V["Y"]), expr(S["successor"], V["X"], V["Y"])
    )

    # (= (later-in-alphabet $X $Y)
    #    (and (successor $X $Z) (later-in-alphabet $Z $Y)))
    m += expr(
        S["="],
        expr(S["later-in-alphabet"], V["X"], V["Y"]),
        expr(
            S["and"],
            expr(S["successor"], V["X"], V["Z"]),
            expr(S["later-in-alphabet"], V["Z"], V["Y"]),
        ),
    )

    # !(test (collapse ((later-in-alphabet d $1) $1))
    #        ((True c) (True b) (True a)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(expr(S["later-in-alphabet"], S["d"], V["1"]), V["1"])),
            expr(
                expr(val(value=True), S["c"]),
                expr(val(value=True), S["b"]),
                expr(val(value=True), S["a"]),
            ),
        )
    )

    yield from ()
