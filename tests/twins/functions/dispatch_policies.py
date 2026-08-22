"""The Python twin of examples/functions/dispatch_policies.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4594


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (only-a A) hit)
    m += expr(S["="], expr(S["only-a"], S["A"]), S["hit"])

    # !(test (only-a B) (only-a B))
    yield m.eval(expr(S["test"], expr(S["only-a"], S["B"]), expr(S["only-a"], S["B"])))

    # !(add-atom &petta (dispatch-policy only-a NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["only-a"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(test (collapse (only-a B)) ())
    yield m.eval(expr(S["test"], expr(S["collapse"], expr(S["only-a"], S["B"])), expr()))

    # !(remove-atom &petta (dispatch-policy only-a NoMatchEnum NoMatchFail))
    yield m.eval(
        expr(
            S["remove-atom"],
            S["&petta"],
            expr(S["dispatch-policy"], S["only-a"], S["NoMatchEnum"], S["NoMatchFail"]),
        )
    )

    # !(test (only-a B) (only-a B))
    yield m.eval(expr(S["test"], expr(S["only-a"], S["B"]), expr(S["only-a"], S["B"])))

    yield from ()
