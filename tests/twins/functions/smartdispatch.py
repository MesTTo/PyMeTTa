"""The Python twin of examples/functions/smartdispatch.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 6852


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (f $x)
    #    (* $x 2))
    m += expr(S["="], expr(S["f"], V["x"]), expr(S["*"], V["x"], 2))

    # (= (g $f $x)
    #    (justdata $f $x))
    m += expr(S["="], expr(S["g"], V["f"], V["x"]), expr(S["justdata"], V["f"], V["x"]))

    # (= (h $f $x)
    #    ($f $x))
    m += expr(S["="], expr(S["h"], V["f"], V["x"]), expr(V["f"], V["x"]))

    # (= (notjustdata $x)
    #    f)
    m += expr(S["="], expr(S["notjustdata"], V["x"]), S["f"])

    # (= (datawithnondatacomponent)
    #    ((lol (f 42))))
    m += expr(S["="], expr(S["datawithnondatacomponent"]), expr(expr(S["lol"], expr(S["f"], 42))))

    # !(test ((f 21) (g f 2) (h f 2) ((notjustdata 42) 21) (datawithnondatacomponent))
    #        (42 (justdata f 2) 4 42 ((lol 84))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                expr(S["f"], 21),
                expr(S["g"], S["f"], 2),
                expr(S["h"], S["f"], 2),
                expr(expr(S["notjustdata"], 42), 21),
                expr(S["datawithnondatacomponent"]),
            ),
            expr(42, expr(S["justdata"], S["f"], 2), 4, 42, expr(expr(S["lol"], 84))),
        )
    )

    yield from ()
