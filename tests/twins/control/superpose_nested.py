"""The Python twin of examples/control/superpose_nested.metta: nesting flattens.

A `superpose` whose elements are themselves superpositions answers every
answer of every element, so `((superpose (a b c)) (superpose (x y z)))`
collapses to six, and mixing superpositions with plain elements works the same
way. That is the whole file: nesting is not a second construct.

`progme` is written at the container door because every answer in it is a
lowercase SYMBOL. A compiled body resolves a lowercase free name as a function
and reads a capitalised one as a constructor, so `a` raises and `A` would
store the wrong atom; wave one recorded that against P14.4 for
`time_and_pragmas`.
"""

from petta import S, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `progme`'s every answer is a lowercase SYMBOL, and a compiled body resolves a lowercase
#: free name as a function and reads a capitalised one as a constructor.
RUNG = "container door for progme, whose every answer is a lowercase symbol"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4844 to 4872, +28, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 4844 by 47554fc's control/types twin baseline.
BUDGET = 4872


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    letters = (S.a, S.b, S.c)
    tail = (S.x, S.y, S.z)

    # (= (progme)
    #    ((collapse (superpose ((superpose (a b c)) (superpose (x y z)))))
    #     (collapse (superpose (a b c)))
    #     (collapse (superpose ((superpose (a b c)))))
    #     (collapse (superpose ((superpose (a b c)) x y z )))))
    m += equation(S.progme()).to(
        (
            S.collapse(S.superpose((S.superpose(letters), S.superpose(tail)))),
            S.collapse(S.superpose(letters)),
            S.collapse(S.superpose((S.superpose(letters),))),
            S.collapse(S.superpose((S.superpose(letters), S.x, S.y, S.z))),
        )
    )

    # !(test (progme) ((a b c x y z) (a b c) (a b c) (a b c x y z)))
    yield m.eval(
        S.test(
            S.progme(),
            (
                (S.a, S.b, S.c, S.x, S.y, S.z),
                letters,
                letters,
                (S.a, S.b, S.c, S.x, S.y, S.z),
            ),
        )
    )
