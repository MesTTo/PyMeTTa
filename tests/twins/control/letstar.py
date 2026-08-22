"""The Python twin of examples/control/letstar.metta: sequential bindings.

Inside a compiled body, `x = 1` IS a `let*` binding: the decorator folds a
statement list into nested `let*` around what follows it. This file has no
definition to hang statements on, though, so the form is built as the term it
is, one `(pattern value)` pair per binding.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 714 to 742, +28, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 714 by 47554fc's control/types twin baseline.
BUDGET = 742


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    yield m.eval(
        S.test(
            S["let*"](
                expr(expr(V.x, 1), expr(V.y, 2)),
                S["+"](V.x, V.y),
            ),
            3,
        )
    )
