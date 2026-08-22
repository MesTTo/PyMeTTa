"""The Python twin of examples/functions/partialdef.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3935


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (mp) (+))
    m += expr(S["="], expr(S["mp"]), expr(S["+"]))

    # !(test (mp 1 1) 2)
    yield m.eval(expr(S["test"], expr(S["mp"], 1, 1), 2))

    # (= (.. $f1 $f2 $arg) ($f1 ($f2 $arg)))
    m += expr(
        S["="], expr(S[".."], V["f1"], V["f2"], V["arg"]), expr(V["f1"], expr(V["f2"], V["arg"]))
    )

    # (= (plus1times2) (.. (* 2) (+ 1)))
    m += expr(S["="], expr(S["plus1times2"]), expr(S[".."], expr(S["*"], 2), expr(S["+"], 1)))

    # !(test (plus1times2 1) 4)
    yield m.eval(expr(S["test"], expr(S["plus1times2"], 1), 4))

    yield from ()
