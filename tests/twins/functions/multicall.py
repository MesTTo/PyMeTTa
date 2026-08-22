"""The Python twin of examples/functions/multicall.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 2295


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (mycalc $x $y)
    #    (+ $x $y))
    m += expr(S["="], expr(S["mycalc"], V["x"], V["y"]), expr(S["+"], V["x"], V["y"]))

    # (= (mycalc $x $y)
    #    (- $x $y))
    m += expr(S["="], expr(S["mycalc"], V["x"], V["y"]), expr(S["-"], V["x"], V["y"]))

    # !(test (collapse (mycalc 1 2))
    #        (3 -1))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["mycalc"], 1, 2)), expr(3, -1)))

    yield from ()
