"""The Python twin of examples/control/case.metta: the first matching branch.

The key 5 misses the literal branch and meets the first variable pattern, so
the answer is 44 and the third branch never runs.

Written at the container door, because a `case` is what Python's `match`
statement would spell and the compiled subset has no lowering for it yet: the
residue table records that against P14.4, which owns the growth. A `case`'s
branches are matched, never evaluated, so they are terms either way.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1501 to 1529, +28, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1501 by 47554fc's control/types twin baseline.
BUDGET = 1529


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (casetest $x)
    #    (case $x ((4 42)
    #              ($otherpattern 44)
    #              ($otherother $45))))
    m += equation(S.casetest(V.x)).to(
        S.case(
            V.x,
            (
                (4, 42),
                (V.otherpattern, 44),
                (V.otherother, V["45"]),
            ),
        )
    )

    # !(test (casetest 5) 44)
    yield m.eval(S.test(S.casetest(5), 44))
