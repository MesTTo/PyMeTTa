"""The Python twin of examples/control/let_superpose_if_case.metta: all four.

One `let` over a four-way `superpose`, an `if` inside it, a `case` inside that,
and the whole thing collapsed: four answers, one per branch of the superpose,
in the superpose's own order.

`f` is a computation and is written as one. `progme` is written at the
container door: its `case` is Python's `match` statement, which the compiled
subset has no lowering for (P14.4), and its answers `answertoeverything` and
the pairs are lowercase data a compiled body has no spelling for.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `progme`'s body is a `case`, which Python's `match` statement would spell and the
#: compiled subset has no lowering for one.
RUNG = "container door for progme, whose case Python's match statement would spell"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5625 to 5934, +309, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 5625 by 47554fc's control/types twin baseline.
BUDGET = 5934


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
    m += equation(S.progme()).to(
        S.let(
            V.y,
            S.superpose((2, 3, 4, 5)),
            S["if"](
                V.y > 2,
                S.case(
                    (1, V.y),
                    (
                        ((1, 3), S.f(0)),
                        ((1, 4), (42, 42)),
                        (V.otherwise, (42, 42, 42)),
                    ),
                ),
                S.answertoeverything,
            ),
        )
    )

    # !(test (collapse (progme))
    #        (answertoeverything 42 (42 42) (42 42 42)))
    yield m.eval(
        S.test(
            S.collapse(S.progme()),
            (
                S.answertoeverything,
                42,
                (42, 42),
                (42, 42, 42),
            ),
        )
    )
