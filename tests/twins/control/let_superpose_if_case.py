"""Purpose: examples/control/let_superpose_if_case.metta in Python: four forms at once.

One equation binds a superposition, tests each answer, dispatches the ones
that pass, and answers a default for the one that fails. Every layer has a
Python statement that means it: a `for` loop over the argument IS
`(superpose (2 3 4 5))` bound by a `let`, the `if` is Python's `if`, and the
`case` over `(1 $y)` fixes its first element on both sides, so what it really
asks is which of 3, 4 or anything else `$y` is, which an `if`/`elif` chain
asks in Python's own words.

`answertoeverything` is capitalised: a compiled body reads a lowercase free
name as a function and a capitalised one as data, the gap case2 records
against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5934 to 7063, +1129 (+19.0%), by the twin contract
#: change: `progme` ENTERED the engine as a compiled `for` loop with an
#: `if`/`elif` chain inside, which is what its `let`, `if` and `case` are,
#: and pays `@m.define`'s fixed registration; the `test` wrapper and the
#: collapse LEFT for `assert` and a list. Measured min-of-3 over fresh
#: processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 9333 the ratio is 0.7568. Prior: 5934,
#: the transliterated twin this replaces.
BUDGET = 7063


def twin(m):
    """Fan out four numbers, filter them, and dispatch what survives."""
    @m.define
    def f(_x):
        # (= (f $x) 42): the head variable the body never reads
        return 42

    @m.define
    def progme():
        # (= (progme)
        #    (let $y (superpose (2 3 4 5))
        #            (if (> $y 2)
        #                (case (1 $y) (((1 3) (f 0)) ((1 4) (42 42)) ($else (42 42 42))))
        #                answertoeverything)))
        for y in (2, 3, 4, 5):
            if y > 2:
                if y == 3:
                    yield f(0)
                elif y == 4:
                    yield 42, 42
                else:
                    yield 42, 42, 42
            else:
                yield Answertoeverything  # noqa: F821  -- a capitalised free name in a compiled body is MeTTa data, which has no Python value to bind

    # !(test (collapse (progme)) (answertoeverything 42 (42 42) (42 42 42)))
    assert progme() == [S.Answertoeverything, 42, Expression((42, 42)), Expression((42, 42, 42))]
