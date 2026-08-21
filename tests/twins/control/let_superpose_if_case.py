"""The Python twin of examples/control/let_superpose_if_case.metta: all four.

One `let` over a four-way `superpose`, an `if` inside it, a `case` inside that,
and the whole thing collapsed: four answers, one per branch of the superpose,
in the superpose's own order.

`f` is a computation and is written as one. `progme` is written at the
container door: its `case` is Python's `match` statement, which the compiled
subset has no lowering for (P14.4), and its answers `answertoeverything` and
the pairs are lowercase data a compiled body has no spelling for.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 5625


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def f(_x):
        # (= (f $x) 42)
        # The parameter is a head variable the body never reads, and the
        # underscore says so to a Python reader.
        return 42

    # (= (progme)
    #    (let $y (superpose (2 3 4 5))
    #                   (if (> $y 2)
    #                       (case (1 $y) (((1 3) (f 0))
    #                                     ((1 4) (42 42))
    #                                     ($else (42 42 42))))
    #                       answertoeverything)))
    m += S["="](
        S.progme(),
        S["let"](
            V.y,
            S["superpose"](expr(2, 3, 4, 5)),
            S["if"](
                S[">"](V.y, 2),
                S["case"](
                    expr(1, V.y),
                    expr(
                        expr(expr(1, 3), f(0)),
                        expr(expr(1, 4), expr(42, 42)),
                        expr(V.otherwise, expr(42, 42, 42)),
                    ),
                ),
                S.answertoeverything,
            ),
        ),
    )

    # !(test (collapse (progme))
    #        (answertoeverything 42 (42 42) (42 42 42)))
    yield m.eval(
        S.test(
            S["collapse"](S.progme()),
            expr(
                S.answertoeverything,
                42,
                expr(42, 42),
                expr(42, 42, 42),
            ),
        )
    )
