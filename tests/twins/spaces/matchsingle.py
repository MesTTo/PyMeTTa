"""The Python twin of examples/spaces/matchsingle.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3764


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (a b)
    m += expr(S["a"], S["b"])

    # (a c)
    m += expr(S["a"], S["c"])

    # (= (match-single-via-cut $space $pattern $outPattern)
    #    (let* (($x (match $space $pattern $outPattern))
    #           ($temp (cut)))
    #          $x))
    m += expr(
        S["="],
        expr(S["match-single-via-cut"], V["space"], V["pattern"], V["outPattern"]),
        expr(
            S["let*"],
            expr(
                expr(V["x"], expr(S["match"], V["space"], V["pattern"], V["outPattern"])),
                expr(V["temp"], expr(S["cut"])),
            ),
            V["x"],
        ),
    )

    # (= (match-single-via-once $space $pattern $outPattern)
    #    (once (match $space $pattern $outPattern)))
    m += expr(
        S["="],
        expr(S["match-single-via-once"], V["space"], V["pattern"], V["outPattern"]),
        expr(S["once"], expr(S["match"], V["space"], V["pattern"], V["outPattern"])),
    )

    # !(test (collapse (match-single-via-cut &self (a $x) (a $x))) ((a b)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match-single-via-cut"],
                    S["&self"],
                    expr(S["a"], V["x"]),
                    expr(S["a"], V["x"]),
                ),
            ),
            expr(expr(S["a"], S["b"])),
        )
    )

    # !(test (collapse (match-single-via-once &self (a $x) (a $x))) ((a b)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match-single-via-once"],
                    S["&self"],
                    expr(S["a"], V["x"]),
                    expr(S["a"], V["x"]),
                ),
            ),
            expr(expr(S["a"], S["b"])),
        )
    )

    yield from ()
