"""The Python twin of examples/control/if4.metta: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does. Every operand here is grounded, so each comparison is spelled
at the naming door rather than with a Python operator, which on two grounded
numbers is Python's own arithmetic.
"""

from petta import S, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `(== 42 42)` and `(+ 2 2)` have two GROUND operands each. Python's `==` is structural
#: equality on atoms rather than a builder, and its method form `val(42).eq(42)` would have to mint
#: an atom the source does not otherwise need; `+` computes the sum.
RUNG = "ground operands: (== 42 42) and (+ 2 2) have two each, where == is structural equality and + computes"

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1108 to 1153, +45, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1108 by 47554fc's control/types twin baseline.
BUDGET = 1153


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    yield m.eval(
        S.test(
            S["if"](
                S["if"](S["=="](42, 42), TRUE, FALSE),
                S["if"](TRUE, 42, S.lol),
                S["+"](2, 2),
            ),
            42,
        )
    )
