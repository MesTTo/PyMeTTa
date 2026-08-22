"""The Python twin of examples/control/tests.metta: four programs composed.

`program4` collapses a three-element expression whose elements each answer
nondeterministically, so the answer is the CROSS PRODUCT: three answers, one
per answer of `program2`, each carrying `program1`'s single collapsed tuple and
`program3`'s single collapsed pair.

Three of the four are computations and are written as ones.

- `program1`: `x = y` is the `let`, and `superpose(12, x + 4)` spells
  `(superpose (12 (+ $x 4)))`, alternatives written out.
- `program3`: `superpose(...)` with ONE argument is `(superpose (...))`,
  a superposition over a single alternative, which is exactly what the
  original writes twice over.
- `program4`: a Python tuple is the expression whose elements are collapsed.

`program2` is written at the container door. Its inner form is
`(superpose $L)`, a superposition over a BOUND value, and `superpose(l)` in a
compiled body means `(superpose ($l))` instead; the residue table records that
against P14.4.

Two of the compiled equations are stored differently from the original's, both
by lowering rather than by choice: an assignment is a one-pair `let*` where the
original writes `let`, and `x == 2` is `(py-eq $x 2)` where it writes
`(== $x 2)`. `program3`'s else arm is a source choice, `return 4` for the
original's `(let $z 4 $z)`, which binds a constant and answers it.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10073 to 10668, +595, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 10073 by 47554fc's control/types twin baseline.
BUDGET = 10668


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # `collapse` and `superpose` are two of the four names a compiled body
    # reads as MeTTa rather than as Python. Binding them here is what keeps
    # the module readable and runnable as Python as well.
    collapse, superpose = m.fn("collapse"), m.fn("superpose")

    @m.define
    def program1(y):
        # (= (program1 $Y) (let $X $Y (collapse (superpose (12 (+ $X 4))))))
        x = y
        return collapse(superpose(12, x + 4))

    # (= (program2 $Y)
    #    (let $list (let $L (1 2 3) (collapse (superpose $L))) (superpose $list)))
    m += equation(S.program2(V.y)).to(
        S.let(
            V.answers,
            S.let(
                V.source,
                (1, 2, 3),
                S.collapse(S.superpose(V.source)),
            ),
            S.superpose(V.answers),
        )
    )
    program2 = m.fn("program2")

    @m.define
    def program3(x):
        # (= (program3 $x)
        #    (if (== $x 2)
        #        (let $z (superpose ((if (< $x 10) (superpose ((42 43))) 43))) $z)
        #        (let $z 4 $z)))
        if x == 2:
            return superpose(superpose((42, 43)) if x < 10 else 43)
        return 4

    @m.define
    def program4():
        # (= (program4) (collapse ((program1 42) (program2 42) (program3 2))))
        return collapse((program1(42), program2(42), program3(2)))

    # !(test (program4)
    #        (((12 46) 1 (42 43)) ((12 46) 2 (42 43)) ((12 46) 3 (42 43))))
    first = (12, 46)
    last = (42, 43)
    yield m.eval(
        S.test(
            S.program4(),
            (
                (first, 1, last),
                (first, 2, last),
                (first, 3, last),
            ),
        )
    )
