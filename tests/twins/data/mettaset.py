"""The Python twin of examples/data/mettaset.metta.

Every source form is rebuilt as atoms through ``S``, ``V``, ``expr``,
and ``val``. Definitions enter through the container protocol and
runnable forms enter through ``m.eval``; no source-reading door is used.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 3573


def twin(m):
    """Yield one answer group per runnable form, in source order."""
    # !(let $x (cons set (superpose ((1 (superpose (a b c)))
    #                                (2 (superpose (d e f)))
    #                                (3 (superpose (a b))))))
    #       (add-atom &self $x))
    yield m.eval(
        expr(
            S["let"],
            V["x"],
            expr(
                S["cons"],
                S["set"],
                expr(
                    S["superpose"],
                    expr(
                        expr(1, expr(S["superpose"], expr(S["a"], S["b"], S["c"]))),
                        expr(2, expr(S["superpose"], expr(S["d"], S["e"], S["f"]))),
                        expr(3, expr(S["superpose"], expr(S["a"], S["b"]))),
                    ),
                ),
            ),
            expr(S["add-atom"], S["&self"], V["x"]),
        )
    )

    # !(test (collapse (match &self (set $x $y) (set $x $y)))
    #        ((set 1 a) (set 1 b) (set 1 c) (set 2 d) (set 2 e) (set 2 f) (set 3 a) (set 3 b)))
    yield m.eval(
        expr(
            S["test"],
            expr(
                S["collapse"],
                expr(
                    S["match"],
                    S["&self"],
                    expr(S["set"], V["x"], V["y"]),
                    expr(S["set"], V["x"], V["y"]),
                ),
            ),
            expr(
                expr(S["set"], 1, S["a"]),
                expr(S["set"], 1, S["b"]),
                expr(S["set"], 1, S["c"]),
                expr(S["set"], 2, S["d"]),
                expr(S["set"], 2, S["e"]),
                expr(S["set"], 2, S["f"]),
                expr(S["set"], 3, S["a"]),
                expr(S["set"], 3, S["b"]),
            ),
        )
    )

    yield from ()
