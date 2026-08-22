"""The Python twin of examples/control/case2.metta: a branch may fork.

One branch, whose pattern is a bare variable so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here.

The equation is written at the container door for the reason case.metta gives:
a `case` is Python's `match` and the compiled subset has no lowering for one
(P14.4). Inside a compiled body `superpose(What, What2)` would spell the
branch value, so the hole is the statement, not the fork.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: a `case` is what Python's `match` statement would spell and the compiled subset has no
#: lowering for one. Inside a compiled body `superpose(What, What2)` would spell the branch VALUE,
#: so the hole is the statement, not the fork.
RUNG = "container door: a case is Python's match statement, which the compiled subset has no lowering for"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1518 to 1546, +28, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1518 by 47554fc's control/types twin baseline.
BUDGET = 1546


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (compile $stmt)
    #    (case $stmt
    #          (($stmt (superpose (what what2))))))
    m += equation(S.compile(V.stmt)).to(
        S.case(
            V.stmt,
            ((V.stmt, S.superpose((S.what, S.what2))),),
        )
    )

    # !(test (collapse (compile wat)) (what what2))
    yield m.eval(S.test(S.collapse(S.compile(S.wat)), (S.what, S.what2)))
