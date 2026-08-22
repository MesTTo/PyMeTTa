"""The Python twin of examples/spaces/spaces3.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4568


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(add-atom &wuspace (wu))
    yield m.eval(expr(S["add-atom"], S["&wuspace"], expr(S["wu"])))

    # !(add-atom &wuspace (wu 42))
    yield m.eval(expr(S["add-atom"], S["&wuspace"], expr(S["wu"], 42)))

    # !(test (collapse (match &wuspace ($1) ($1))) ((wu)))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["match"], S["&wuspace"], expr(V["1"]), expr(V["1"]))),
            expr(expr(S["wu"])),
        )
    )

    # !(test (collapse (match &wuspace ($1) (hu $1))) ((hu wu)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"], expr(S["match"], S["&wuspace"], expr(V["1"]), expr(S["hu"], V["1"]))
            ),
            expr(expr(S["hu"], S["wu"])),
        )
    )

    # !(test (collapse (match &wuspace ($1) $1)) (wu))
    yield m.eval(
        expr(
            S["test"],
            expr(S["collapse"], expr(S["match"], S["&wuspace"], expr(V["1"]), V["1"])),
            expr(S["wu"]),
        )
    )

    # !(test (msort (collapse (match &wuspace $1 $1))) (msort (collapse (get-atoms &wuspace))))
    yield m.eval(
        expr(
            S["test"],
            expr(S["msort"], expr(S["collapse"], expr(S["match"], S["&wuspace"], V["1"], V["1"]))),
            expr(S["msort"], expr(S["collapse"], expr(S["get-atoms"], S["&wuspace"]))),
        )
    )

    # !(test (msort (collapse (match &wuspace $1 (wu $1)))) ((wu (wu)) (wu (wu 42))))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["msort"],
                expr(S["collapse"], expr(S["match"], S["&wuspace"], V["1"], expr(S["wu"], V["1"]))),
            ),
            expr(expr(S["wu"], expr(S["wu"])), expr(S["wu"], expr(S["wu"], 42))),
        )
    )

    yield from ()
