"""The Python twin of examples/control/letext.metta: `let` matches a pattern.

`let` binds by MATCHING a pattern against a value, not by naming a variable:
here `($x (42 (if (== $x 2) 43 44)))` meets `(3 (42 $z))`, so `$x` takes 3 and
`$z` takes the still-unrun `(if (== 3 2) 43 44)`, which the body then
evaluates to 44. `(+ 3 44)` is 47.

Nothing about that is a Python assignment, so the whole form is a term.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1222 to 1264, +42, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1222 by 47554fc's control/types twin baseline.
BUDGET = 1264


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (let ($x (42 (if (== $x 2) 43 44))) (3 (42 $z)) (+ $x $z)) 47)
    yield m.eval(
        S.test(
            S["let"](
                expr(V.x, expr(42, S["if"](S["=="](V.x, 2), 43, 44))),
                expr(3, expr(42, V.z)),
                S["+"](V.x, V.z),
            ),
            47,
        )
    )
