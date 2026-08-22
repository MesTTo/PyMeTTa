"""The Python twin of examples/control/empty.metta: a function that answers nothing.

Answering nothing is not answering `()`: `collapse` over no answers is the
empty expression, and that is what the original asserts.

`empty` is one of the four names a compiled body reads as MeTTa rather than as
Python (`match`, `superpose`, `collapse`, `empty`), so

    @m.define
    def y():
        return empty()

does write this equation. It is not what this twin does, and the reason is a
measurement rather than a preference: `@m.define` costs about 1,561 inferences
per definition over the same equation written as an atom, and the whole
original costs 2,498, so the decorator's fixed cost alone puts the twin 12%
past the lane's 10% band. The container door lands the identical atom for the
identical compiled clauses. identity.metta is the same choice made the same
way in `basics/`; the ladder documents both rungs and a twin picks the one the
original's size calls for.
"""

from petta import S, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1081 to 1116, +35, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1081 by 47554fc's control/types twin baseline.
BUDGET = 1116


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (y) (empty))
    m += S["="](S.y(), S["empty"]())

    # !(test (collapse (y)) ())
    yield m.eval(S.test(S["collapse"](S.y()), expr()))
