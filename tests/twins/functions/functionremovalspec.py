"""The Python twin of examples/functions/functionremovalspec.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 10048


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (g $x) (+ $x 1))
    m += expr(S["="], expr(S["g"], V["x"]), expr(S["+"], V["x"], 1))

    # (= (f $g) ($g 1))
    m += expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 1))

    # (= (f $g) ($g 2))
    m += expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 2))

    # !(test (collapse (f g)) (2 3))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["f"], S["g"])), expr(2, 3)))

    # !(remove-atom &self (= (f $g) ($g 1)))
    yield m.eval(
        expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 1)))
    )

    # !(test (f g) 3)
    yield m.eval(expr(S["test"], expr(S["f"], S["g"]), 3))

    # !(add-atom &self (= (f $g) ($g 1)))
    yield m.eval(
        expr(S["add-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 1)))
    )

    # !(test (f g) (3 2))
    yield m.eval(expr(S["test"], expr(S["f"], S["g"]), expr(3, 2)))

    yield from ()
