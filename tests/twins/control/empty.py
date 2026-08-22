"""The Python twin of examples/control/empty.metta: a function that answers nothing.

Answering nothing is not answering `()`: `collapse` over no answers is the
empty expression, and that is what the original asserts.

`empty` is one of the four names a compiled body reads as MeTTa rather than as
Python (`match`, `superpose`, `collapse`, `empty`), so the definition is an
ordinary Python function and the decorator writes the equation.

This twin used to sit at the container door on a cost argument that is no
longer true. The claim was that `@m.define`'s fixed registration cost put the
twin 12% past the lane's 10% band; re-measured 2026-08-22 the decorator costs
2,745 against the original's 2,508, a ratio of 1.0945, which is inside the
band. `basics/identity.metta` is the same shape and still does NOT fit, at
2,878 against a ceiling of 2,835, so the two files now differ by 43 inferences
rather than by preference.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1116 to 2745, +1629 (+145.97%), by lifting the
#: equation from the container door to `@m.define`. The whole of the increase
#: is the decorator's fixed registration cost: reading the body as syntax,
#: deriving the definition facts and installing the equation. The equation
#: stored and the clauses compiled are identical either way, so the running
#: cost of `(y)` did not move; three fresh processes measured 2745, 2745,
#: 2745, against the original's 2508 and the lane's ceiling of 2758.
#: Prior: RE-PINNED 2026-08-22, 1081 to 1116, +35, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1081 by 47554fc's control/types twin baseline.
BUDGET = 2745


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def y():
        # (= (y) (empty))
        return empty()  # noqa: F821  -- empty is one of the four names a compiled body reads as MeTTa

    # !(test (collapse (y)) ())
    yield m.eval(S.test(S.collapse(S.y()), ()))
