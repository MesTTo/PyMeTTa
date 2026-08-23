"""Purpose: examples/control/let_superpose_if_case.metta in Python: four forms at once.

One equation binds a superposition, tests each answer, dispatches the ones
that pass, and answers a default for the one that fails. Every layer has a
Python statement that means it: a `for` loop over the argument IS
`(superpose (2 3 4 5))` bound by a `let`, the `if` is Python's `if`, and the
`case` over `(1 $y)` fixes its first element on both sides, so what it really
asks is which of 3, 4 or anything else `$y` is, which an `if`/`elif` chain
asks in Python's own words.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


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
        # The top rung writes the inner dispatch as the `case` it is:
        #
        #     match 1, y:
        #         case (1, 3): yield f(0)
        #         case (1, 4): yield 42, 42
        #         case _: yield 42, 42, 42
        #
        # `ast.Match` has no lowering in the compiled subset, so the arms are
        # an if/elif chain, which asks the same question because the `case`
        # fixes its first element on both sides. Residue: P14.4.
        for y in (2, 3, 4, 5):
            if y > 2:
                if y == 3:
                    yield f(0)
                elif y == 4:
                    yield 42, 42
                else:
                    yield 42, 42, 42
            else:
                yield S.answertoeverything

    # !(test (collapse (progme)) (answertoeverything 42 (42 42) (42 42 42)))
    assert progme() == [S.answertoeverything, 42, Expression((42, 42)), Expression((42, 42, 42))]
