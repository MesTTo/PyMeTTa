"""The Python twin of examples/data/streamops.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4650


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(test (collapse (unique (superpose (a b c d d)))) (a b c d))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["unique"], expr(S["superpose"], expr(S["a"], S["b"], S["c"], S["d"], S["d"]))
                ),
            ),
            expr(S["a"], S["b"], S["c"], S["d"]),
        )
    )

    # !(test (collapse (union (superpose (a b b c)) (superpose (b c c d)))) (a b b c b c c d))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["union"],
                    expr(S["superpose"], expr(S["a"], S["b"], S["b"], S["c"])),
                    expr(S["superpose"], expr(S["b"], S["c"], S["c"], S["d"])),
                ),
            ),
            expr(S["a"], S["b"], S["b"], S["c"], S["b"], S["c"], S["c"], S["d"]),
        )
    )

    # !(test (collapse (intersection (superpose (a b c c)) (superpose (b c c c d)))) (b c c))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["intersection"],
                    expr(S["superpose"], expr(S["a"], S["b"], S["c"], S["c"])),
                    expr(S["superpose"], expr(S["b"], S["c"], S["c"], S["c"], S["d"])),
                ),
            ),
            expr(S["b"], S["c"], S["c"]),
        )
    )

    # !(test (collapse (subtraction (superpose (a b b c)) (superpose (b c c d)))) (a b))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["subtraction"],
                    expr(S["superpose"], expr(S["a"], S["b"], S["b"], S["c"])),
                    expr(S["superpose"], expr(S["b"], S["c"], S["c"], S["d"])),
                ),
            ),
            expr(S["a"], S["b"]),
        )
    )

    yield from ()
