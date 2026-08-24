"""Purpose: examples/control/tests.metta in Python: four programs, one answer set.

`program4` collapses a three-element expression whose middle element answers
three times, so the whole thing answers three times and the collapse gathers
all three. The other three programs are the ways a `let` and a superposition
can be stacked, and each has a Python statement that means it: `let` is
assignment, `superpose` over written-out alternatives is the form itself, and
`superpose` over a BOUND expression is `fn.superpose`, one rung down because
the ruled `superpose(*xs)` refuses inside a body ["Starred has no MeTTa
equivalent in the compiled subset", measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7] and
`superpose(xs)` is the other operation.

`collapse` is the one name here Python's own linter cannot see: `superpose`
and `match` are package exports now, `collapse` and `empty` are not, so a
compiled body that gathers carries the suppression the residue entry against
P14.4 would delete. `list()`, the dissolution table's spelling for `collapse`,
does not lower inside a compiled body either, which supercollapse records
against the same row.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, fn, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Stack lets and superpositions four ways, then collapse the lot."""
    @m.define
    def program1(y):
        # (= (program1 $Y) (let $X $Y (collapse (superpose (12 (+ $X 4))))))
        x = y
        return collapse(superpose(12, x + 4))  # noqa: F821  -- `collapse` is a name a compiled body reads as MeTTa, which the package exports nowhere yet (residue, P14.4)

    @m.define
    def program2(_y):
        # (= (program2 $Y) (let $list (let $L (1 2 3) (collapse (superpose $L))) (superpose $list)))
        values = (1, 2, 3)
        answers = collapse(fn.superpose(values))  # noqa: F821  -- the same name
        return fn.superpose(answers)

    @m.define
    def program3(x):
        # (= (program3 $x)
        #    (if (== $x 2)
        #        (let $z (superpose ((if (< $x 10) (superpose ((42 43))) 43))) $z)
        #        (let $z 4 $z)))
        # Python's `==` lowers to `py-eq`, its own equality rather than
        # MeTTa's `==`; both answer the same here, and the `let`s that only
        # name their own result are the identity a Python reader would drop.
        if x == 2:
            return superpose(superpose((42, 43)) if x < 10 else 43)
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
