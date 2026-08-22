"""The Python twin of examples/control/if3.metta: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs. `V.A` is that variable, and the
lane compares answers up to consistent renaming, so the letter carries no
weight.
"""

from petta import S, V, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: the else arm `(+ 2 2)` is DATA with two GROUND operands, where Python's `+` computes
#: the sum instead of building the term.
RUNG = "ground operands: the else arm (+ 2 2) has two, where Python's + computes the sum"

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 915 to 955, +40, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 915 by 47554fc's control/types twin baseline.
BUDGET = 955


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    yield m.eval(
        S.test(
            S["if"](
                S["is-var"](V.A),
                S["if"](TRUE, 42, S.lol),
                S["+"](2, 2),
            ),
            42,
        )
    )
