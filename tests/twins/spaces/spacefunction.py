"""The Python twin of examples/spaces/spacefunction.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 5262


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &self (= (f $x $y) (+ $x $y)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&self"],
            expr(S["="], expr(S["f"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
        )
    )

    # !(add-atom &self (= (g $x $y) (+ $x $y)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&self"],
            expr(S["="], expr(S["g"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
        )
    )

    # !(remove-atom &self (= (f $x $y) (+ $x $y)))
    yield m.eval(
        expr(
            S["remove-atom"],
            S["&self"],
            expr(S["="], expr(S["f"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"])),
        )
    )

    # !(test (f 3 4) (f 3 4))
    yield m.eval(expr(S["test"], expr(S["f"], 3, 4), expr(S["f"], 3, 4)))

    # !(test (g 3 4) 7)
    yield m.eval(expr(S["test"], expr(S["g"], 3, 4), 7))

    # !(add-atom &self (my test))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["my"], S["test"])))

    # !(remove-atom &self (my test))
    yield m.eval(expr(S["remove-atom"], S["&self"], expr(S["my"], S["test"])))

    # !(test (collapse (match &self (my test) (my test))) ())
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(S["match"], S["&self"], expr(S["my"], S["test"]), expr(S["my"], S["test"])),
            ),
            expr(),
        )
    )

    yield from ()
