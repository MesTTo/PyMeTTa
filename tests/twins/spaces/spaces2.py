"""The Python twin of examples/spaces/spaces2.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3575


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # (foo 1)
    m += expr(S["foo"], 1)

    # (foo 2)
    m += expr(S["foo"], 2)

    # (foo 42 42)
    m += expr(S["foo"], 42, 42)

    # (foo (42 42))
    m += expr(S["foo"], expr(42, 42))

    # !(bar 42)
    yield m.eval(expr(S["bar"], 42))

    # !(bar 43)
    yield m.eval(expr(S["bar"], 43))

    # (= (answer) 42)
    m += expr(S["="], expr(S["answer"]), 42)

    # !(test (space (msort (collapse (superpose ((match &self (foo $1) (foo $1))
    #                                            (match &self (foo $1 $2) (foo $1 $2))
    #                                            (match &self (bar $1) (bar $1)))))) (answer))
    #        (space ((foo 1) (foo 2) (foo 42 42) (foo (42 42))) 42))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["space"],
                expr(
                    S["msort"],
                    expr(
                        S["collapse"],
                        expr(
                            S["superpose"],
                            expr(
                                expr(
                                    S["match"],
                                    S["&self"],
                                    expr(S["foo"], V["1"]),
                                    expr(S["foo"], V["1"]),
                                ),
                                expr(
                                    S["match"],
                                    S["&self"],
                                    expr(S["foo"], V["1"], V["2"]),
                                    expr(S["foo"], V["1"], V["2"]),
                                ),
                                expr(
                                    S["match"],
                                    S["&self"],
                                    expr(S["bar"], V["1"]),
                                    expr(S["bar"], V["1"]),
                                ),
                            ),
                        ),
                    ),
                ),
                expr(S["answer"]),
            ),
            expr(
                S["space"],
                expr(
                    expr(S["foo"], 1),
                    expr(S["foo"], 2),
                    expr(S["foo"], 42, 42),
                    expr(S["foo"], expr(42, 42)),
                ),
                42,
            ),
        )
    )

    yield from ()
