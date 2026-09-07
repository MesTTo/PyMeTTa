"""examples/ch08-data/08-01-atoms-lists-and-folds/20-roman_general_operators.metta in Python: three set operations with the comparison passed in.

The nine fixed spellings `15-roman.metta` uses are one call each to these
three with an equality supplied, so this file supplies one of its own. The
operator names are punctuation Python's grammar will not take, so all three
come through the exact subscript door, which is rung 5.

`close-enough` is an ordinary compiled definition, and the operators take its
NAME rather than a call, which is what makes them higher-order. Its comparison
is built by its WORD, `fn.lt(...)`, because `<` is not one of the five number
operators a compiled body lowers natively and `a < b` would store
`(py-operator lt ...)` where the original stores `(< ...)`.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, fn, lib

#: The two collections every claim is about.
LEFT = (1, 5, 9)
RIGHT = (2, 100)


def twin(m):
    """Intersection, subtraction and union under a comparison of our own."""
    m += lib.roman

    @m.define
    def close_enough(a: int, b: int) -> bool:
        # (= (close-enough $a $b) (< (abs-math (- $a $b)) 2))
        return fn.lt(fn.abs_math(a - b), 2)

    near = S.close_enough
    intersect, subtract, union = m.fn["/?\\"], m.fn["\\?"], m.fn["\\?/"]

    # `/?\` keeps the elements of the left the comparison relates to
    # something on the right.
    assert intersect(near, LEFT, RIGHT) == [(1,)]
    assert intersect(near, LEFT, ()) == [()]

    # `\?` is the other half: the elements with no relative on the right.
    assert subtract(near, LEFT, RIGHT) == [(5, 9)]
    assert subtract(near, LEFT, ()) == [LEFT]

    # `\?/` is the union built out of that subtraction.
    assert union(near, LEFT, RIGHT) == [(5, 9, 2, 100)]
    assert union(near, (), RIGHT) == [RIGHT]

    # Passing `==` back in reproduces the fixed spelling exactly, which is
    # what makes the nine sugar over three operations.
    equals = S["=="]
    assert intersect(equals, (1, 2, 3), (2, 3, 4)) == m.fn["/==\\"]((1, 2, 3), (2, 3, 4))
    assert subtract(equals, (1, 2, 3), (2, 3, 4)) == m.fn["\\=="]((1, 2, 3), (2, 3, 4))
    assert union(equals, (1, 2, 3), (2, 3, 4)) == m.fn["\\==/"]((1, 2, 3), (2, 3, 4))

    # `fst` and `snd` read a two-element expression, and `cns` is the pair
    # reading of `cons`.
    assert m.fn.fst((S.a, S.b)) == [S.a]
    assert m.fn.snd((S.a, S.b)) == [S.b]
    assert m.fn.cns((1, (2, 3))) == [(1, 2, 3)]
    assert m.fn.cns((S.f(1), ())) == [(S.f(1),)]

    # The two tracing helpers print and answer their subject unchanged.
    assert m.fn.traceid(42) == [42]
    assert m.fn.tracem(G("the answer"), 42) == [42]
    assert m.answers(1 + S.traceid(41)) == [42]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 132148 inferences, 1.0705x the example's 123442; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 132148
