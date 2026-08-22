"""The Python twin of examples/functions/functionremoval.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 10071


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (g $x) (+ $x 1))
    m += expr(S["="], expr(S["g"], V["x"]), expr(S["+"], V["x"], 1))

    # (= (f $g) ($g 1))
    m += expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 1))

    # (= (f $g) 42)
    m += expr(S["="], expr(S["f"], V["g"]), 42)

    # !(test (collapse (f g)) (2 42))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["f"], S["g"])), expr(2, 42)))

    # !(remove-atom &self (= (f $g) 42))
    yield m.eval(expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), 42)))

    # !(test (collapse (f g)) (2))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["f"], S["g"])), expr(2)))

    # !(add-atom &self (= (f $g) 42))
    yield m.eval(expr(S["add-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), 42)))

    # !(remove-atom &self (= (f $g) ($g 1)))
    yield m.eval(
        expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), expr(V["g"], 1)))
    )

    # !(test (collapse (f g)) (42))
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["f"], S["g"])), expr(42)))

    # !(remove-atom &self (= (f $g) 42))
    yield m.eval(expr(S["remove-atom"], S["&self"], expr(S["="], expr(S["f"], V["g"]), 42)))

    # !(test (collapse (f g)) ((f g)))
    yield m.eval(
        expr(S["test"], expr(S["collapse"], expr(S["f"], S["g"])), expr(expr(S["f"], S["g"])))
    )

    yield from ()
