"""Purpose: examples/control/tests.metta in Python: four programs, one answer set.

`program4` collapses a three-element expression whose middle element answers
three times, so the whole thing answers three times and the collapse gathers
all three. The other three programs are the ways a `let` and a superposition
can be stacked, and each has a Python statement that means it: `let` is
assignment, `superpose` over written-out alternatives is the form itself, and
`superpose` over a BOUND expression is `yield from`.

`collapse` and `superpose` are bound from `m.fn` so that names a compiled body
reads as MeTTa are names Python can see too; `list()` does not lower to
`collapse` inside a compiled body, which supercollapse records against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10668 to 8999, -1669 (-15.6%), by the twin contract
#: change: `program2` ENTERED the engine as a compiled generator where it was
#: a container-door equation, and the `test` wrapper LEFT for `assert`; the
#: collapse inside `program4` still runs there, which is the file's subject.
#: Measured min-of-3 over fresh processes with the MORK backend linked in,
#: which the artefact-free worktree omits and which moves a compiled twin by
#: about 10 inferences per definition; against the example's 15006 the ratio
#: is 0.5997. Prior: 10668, the transliterated twin this replaces.
BUDGET = 8999


def twin(m):
    """Stack lets and superpositions four ways, then collapse the lot."""
    collapse, superpose = m.fn("collapse"), m.fn("superpose")

    @m.define
    def program1(y):
        # (= (program1 $Y) (let $X $Y (collapse (superpose (12 (+ $X 4))))))
        x = y
        return collapse(superpose(12, x + 4))

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
            return superpose(superpose((42, 43)) if x < 10 else 43)
        return 4

    @m.define
    def program4():
        # (= (program4) (collapse ((program1 42) (program2 42) (program3 2))))
        return collapse((program1(42), program2(42), program3(2)))

    first = Expression((12, 46))
    last = Expression((42, 43))

    # !(test (program4)
    #        (((12 46) 1 (42 43)) ((12 46) 2 (42 43)) ((12 46) 3 (42 43))))
    assert program4() == [Expression(Expression((first, n, last)) for n in (1, 2, 3))]
