"""The Python twin of examples/control/if.metta: three-argument `if`.

Both arms are EXPRESSIONS, `(3 4)` and `(5 6)`, and a Python tuple IS one: a
tuple encodes to the expression of its encoded elements, so `(3, 4)` is `(3 4)`
and needs no builder.

The condition is a term over two grounded numbers, which the naming door
spells: `1 > 2` in Python is Python's own comparison and answers `False`
before any atom exists, so `S[">"](1, 2)` is how a comparison stays a term.
"""

from petta import S

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `(> 1 2)` has two GROUND operands, where Python's `>` computes the comparison and
#: answers `False` before any atom exists.
RUNG = "ground operands: (> 1 2) has two, where Python's > computes the comparison"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 852 to 887, +35, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 852 by 47554fc's control/types twin baseline.
BUDGET = 887


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (if (> 1 2) (3 4) (5 6)) (5 6))
    yield m.eval(S.test(S["if"](S[">"](1, 2), (3, 4), (5, 6)), (5, 6)))
