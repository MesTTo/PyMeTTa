"""The Python twin of examples/control/caseempty.metta: the `Empty` branch.

`Empty` is the branch a key with NO ANSWERS takes. In `wu` the key is
`(empty)`, so the default fires and the answer is 42; in `wu2` the key answers
42, so the ordinary branch fires and `Empty` is not reached. The pair is the
whole file: `Empty` is about the absence of an answer, not about the value
`()`.

`f` is the one equation here that is a computation, so it is written as one.
The two `case` equations are written at the container door, since Python's
`match` statement has no lowering yet (P14.4).
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
BUDGET = 4710


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (wu) (case (empty) ((1 2) (Empty 42))))
    m += S["="](
        S.wu(),
        S["case"](
            S["empty"](),
            expr(expr(1, 2), expr(S.Empty, 42)),
        ),
    )

    @m.define
    def f():
        # (= (f) 42)
        return 42

    # (= (wu2) (case (f) ((42 ok) (Empty nok))))
    m += S["="](
        S.wu2(),
        S["case"](f(), expr(expr(42, S.ok), expr(S.Empty, S.nok))),
    )

    # !(test (wu) 42)
    yield m.eval(S.test(S.wu(), 42))
    # !(test (wu2) ok)
    yield m.eval(S.test(S.wu2(), S.ok))
