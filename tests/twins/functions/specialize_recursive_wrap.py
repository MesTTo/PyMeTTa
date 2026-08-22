"""The Python twin of examples/functions/specialize_recursive_wrap.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 9800


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (= (derive $g) $g)
    m += expr(S["="], expr(S["derive"], V["g"]), V["g"])

    # (= (twice $r $g) ($r ($r $g)))
    m += expr(S["="], expr(S["twice"], V["r"], V["g"]), expr(V["r"], expr(V["r"], V["g"])))

    # (= (evolve $r $n $g) (if (== $n 0) $g (evolve (twice $r) (- $n 1) $g)))
    m += expr(
        S["="],
        expr(S["evolve"], V["r"], V["n"], V["g"]),
        expr(
            S["if"],
            expr(S["=="], V["n"], 0),
            V["g"],
            expr(S["evolve"], expr(S["twice"], V["r"]), expr(S["-"], V["n"], 1), V["g"]),
        ),
    )

    # !(test (evolve derive 2 stmt) stmt)
    yield m.eval(expr(S["test"], expr(S["evolve"], S["derive"], 2, S["stmt"]), S["stmt"]))

    yield from ()
