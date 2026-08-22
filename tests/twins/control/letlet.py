"""The Python twin of examples/control/letlet.metta: a destructuring binding.

The equation is written at the container door because its `let*` binding is a
PATTERN, `(($f1 $c1 3) (1 2 $d1))`: three variables and a literal on the left
meeting three values on the right, binding in both directions at once. Python
spells that `f1, c1, _ = 1, 2, d1`, and a compiled body refuses a tuple target
("a compiled body binds plain names; destructuring and attribute assignment
have no let* form"). The residue table records that against P14.4.

So the ladder's other rung carries it: `m += equation(head).to(body)` lands exactly
the atom the file lands, with no string anywhere.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: the `let*` binding is a destructuring PATTERN, and a compiled body binds plain names:
#: "destructuring and attribute assignment have no let* form".
RUNG = "container door for f, whose let* binding is a destructuring pattern"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1681 to 1709, +28, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 1681 by 47554fc's control/types twin baseline.
BUDGET = 1709


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (f) (let* ((($f1 $c1 3) (1 2 $d1))) ($f1 $c1 $d1)))
    m += equation(S.f()).to(
        S["let*"](
            (((V.f1, V.c1, 3), (1, 2, V.d1)),),
            (V.f1, V.c1, V.d1),
        )
    )

    # !(test (f) (1 2 3))
    yield m.eval(S.test(S.f(), (1, 2, 3)))
