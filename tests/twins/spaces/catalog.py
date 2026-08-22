"""The Python twin of examples/spaces/catalog.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4820


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (match &petta (vocabulary fidelity $a $b $c $d) ($a $b $c $d))
    #        (Exact Partial Sound Refuse))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["vocabulary"], S["fidelity"], V["a"], V["b"], V["c"], V["d"]),
                expr(V["a"], V["b"], V["c"], V["d"]),
            ),
            expr(S["Exact"], S["Partial"], S["Sound"], S["Refuse"]),
        )
    )

    # !(test (match &petta (kind handles $ctx $entry $claim $det) $claim)
    #        (one-of fidelity))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["kind"], S["handles"], V["ctx"], V["entry"], V["claim"], V["det"]),
                V["claim"],
            ),
            expr(S["one-of"], S["fidelity"]),
        )
    )

    # !(test (match &petta (claim semiring ranked $p) $p) ordered)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["claim"], S["semiring"], S["ranked"], V["p"]),
                V["p"],
            ),
            S["ordered"],
        )
    )

    # !(add-atom &petta (vocabulary freshness-level live cached stale))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["vocabulary"], S["freshness-level"], S["live"], S["cached"], S["stale"]),
        )
    )

    # !(add-atom &petta (kind freshness symbol pattern (one-of freshness-level)))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(
                S["kind"],
                S["freshness"],
                S["symbol"],
                S["pattern"],
                expr(S["one-of"], S["freshness-level"]),
            ),
        )
    )

    # !(add-atom &petta (freshness &rows (edge $a $b) cached))
    yield m.eval(
        expr(
            S["add-atom"],
            S["&petta"],
            expr(S["freshness"], S["&rows"], expr(S["edge"], V["a"], V["b"]), S["cached"]),
        )
    )

    # !(test (match &petta (freshness &rows $shape $level) $level) cached)
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["match"],
                S["&petta"],
                expr(S["freshness"], S["&rows"], V["shape"], V["level"]),
                V["level"],
            ),
            S["cached"],
        )
    )

    # !(add-atom &petta (routed-by-shape freshness))
    yield m.eval(expr(S["add-atom"], S["&petta"], expr(S["routed-by-shape"], S["freshness"])))

    # !(test (match &petta (routed-by-shape freshness) found) found)
    yield m.eval(
        expr(
            S["test"],
            expr(S["match"], S["&petta"], expr(S["routed-by-shape"], S["freshness"]), S["found"]),
            S["found"],
        )
    )

    yield from ()
