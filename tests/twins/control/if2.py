"""The Python twin of examples/control/if2.metta: a symbol is not a variable.

`(is-var a)` asks about the ATOM `a`, so the answer is False and the else arm
runs. `S.a` is that atom; a Python name `a` would be a Python binding and
never reach the engine.

The then arm `(() (+ 1 1))` is an expression whose first element is the empty
expression, and Python's own empty tuple is that atom, so `((), ...)` spells it:
`()` is a term, not a hole.
"""

from petta import S

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `(+ 1 1)` and `(+ 2 2)` are arms `if` is handed as DATA and have two GROUND operands
#: each, where Python's `+` computes the sum instead of building the term.
RUNG = (
    "ground operands: the arms (+ 1 1) and (+ 2 2) have two each, where Python's + computes the sum"
)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1138 to 1187, +49, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1138 by 47554fc's control/types twin baseline.
BUDGET = 1187


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (is-var a) (() (+ 1 1)) (+ 2 2)) 4)
    yield m.eval(
        S.test(
            S["if"](
                S["is-var"](S.a),
                ((), S["+"](1, 1)),
                S["+"](2, 2),
            ),
            4,
        )
    )
