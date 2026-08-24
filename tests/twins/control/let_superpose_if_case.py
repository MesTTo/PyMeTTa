"""Purpose: examples/control/let_superpose_if_case.metta in Python: four forms at once.

One equation binds a superposition, tests each answer, dispatches the ones
that pass, and answers a default for the one that fails. Every layer has a
Python statement that means it, and the equation the four of them compile to
is the original's own: an assignment IS the `let`, `superpose(...)` in
expression position IS the superposition, the `if` is Python's `if`, and the
`case` over `(1 $y)` is Python's `match` statement, arms and fallback
included.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
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
        y = superpose(2, 3, 4, 5)
        if y > 2:
            match 1, y:
                case (1, 3):
                    return f(0)
                case (1, 4):
                    return 42, 42
                case _:
                    return 42, 42, 42
        return S.answertoeverything

    # !(test (collapse (progme)) (answertoeverything 42 (42 42) (42 42 42)))
    assert progme() == [S.answertoeverything, 42, Expression((42, 42)), Expression((42, 42, 42))]
