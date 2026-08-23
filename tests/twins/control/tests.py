"""Purpose: examples/control/tests.metta in Python: four programs, one answer set.

`program4` collapses a three-element expression whose middle element answers
three times, so the whole thing answers three times and the collapse gathers
all three. The other three programs are the ways a `let` and a superposition
can be stacked, and each has a Python statement that means it: `let` is
assignment, `superpose` over written-out alternatives is the form itself, and
`superpose` over a BOUND expression is `yield from`.

`collapse` and `superpose` are names a compiled body reads as MeTTa and
Python's own linter does not, so each carries the suppression the residue
entry against P14.4 would delete; `list()` does not lower to `collapse` inside
a compiled body either, which supercollapse records against the same row.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Stack lets and superpositions four ways, then collapse the lot."""
    # The top rung imports the two names, so Python's own linter sees them:
    #     from petta import collapse, superpose
    # The package exports neither, so each call carries an F821 suppression, and
    # `list()`, the dissolution table's spelling for `collapse`, does not
    # lower inside a compiled body. Residue: P14.4.
    @m.define
    def program1(y):
        # (= (program1 $Y) (let $X $Y (collapse (superpose (12 (+ $X 4))))))
        x = y
        return collapse(superpose(12, x + 4))  # noqa: F821  -- names a compiled body reads as MeTTa, which the package exports nowhere yet (residue, P14.4)

    @m.define
    def program2(_y):
        # (= (program2 $Y) (let $list (let $L (1 2 3) (collapse (superpose $L))) (superpose $list)))
        # Fanning an expression out and gathering it back gives that same
        # expression, so the inner `let` is an ordinary binding and the outer
        # `(superpose $list)` is `yield from`.
        answers = (1, 2, 3)
        yield from answers

    @m.define
    def program3(x):
        # (= (program3 $x)
        #    (if (== $x 2)
        #        (let $z (superpose ((if (< $x 10) (superpose ((42 43))) 43))) $z)
        #        (let $z 4 $z)))
        if x == 2:
            return superpose(superpose((42, 43)) if x < 10 else 43)  # noqa: F821  -- the same name
        return 4

    @m.define
    def program4():
        # (= (program4) (collapse ((program1 42) (program2 42) (program3 2))))
        return collapse((program1(42), program2(42), program3(2)))  # noqa: F821  -- the same name

    first = Expression((12, 46))
    last = Expression((42, 43))

    # !(test (program4)
    #        (((12 46) 1 (42 43)) ((12 46) 2 (42 43)) ((12 46) 3 (42 43))))
    rows = tuple(Expression((first, n, last)) for n in (1, 2, 3))
    assert program4() == [Expression(rows)]
