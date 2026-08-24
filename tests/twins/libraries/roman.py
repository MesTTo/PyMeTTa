"""Purpose: examples/libraries/roman.metta in Python: lib_roman, walked end to end.

Every claim here is about a lib_roman function, so every one names it. Three
families: the higher-order maps and folds, the nine set operations whose names
are drawn from the shapes of their Venn diagrams, and the composition
combinators. Then the inverses: `let` unifying a CALL against a value so the
function runs BACKWARDS, where `(let (head $x) (1 2 3) $x)` answers 1 because
head, run in reverse, says what its argument's first element must be. `solve`
is the door for that shape, and its answer template takes the variables the
PATTERN introduces as well as the subject's, which is what this reading needs.

Six of the nine set operations carry VARIABLES in their arguments, and the
call answers the resulting term all the same. Two of those answers carry a
fresh variable, which is why they are compared with `alpha_eq` rather than
`==`: the engine renames variables and the claim is about the shape, not the
name.

An engine function may be named with an ampersand, and three of these are:
`&&&`, `&^&` and the Venn family's punctuation take the bracket, which is the
exact door for a name Python's grammar cannot spell. The arithmetic the maps
and folds are GIVEN takes the other door in the same ladder: `+` and `*` have
words, so `S.add(1)` is the partial application `(+ 1)` and `S.add` alone is
the operator mentioned by name.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import lib_roman, then exercise its three families and its inverses."""
    m.fn["import!"](m, S.library(S["lib_roman"]))

    # Higher-order functions.
    assert m.fn.map_flat(S.add(1), (1, 2, 3)) == [Expression((2, 3, 4))]
    assert m.fn.map_nested(S.add(1), (1, (2, 3))) == [
        Expression((2, Expression((3, 4))))
    ]
    assert m.fn.fold_flat(S.add, 0, (1, 2, 3)) == [6]
    assert m.fn.foldr_flat(S.cons, (), (1, (2, 3), 4)) == [
        Expression((1, Expression((2, 3)), 4))
    ]
    assert m.fn.fold_nested(S.add, 0, (1, (2, 3))) == [6]

    # Set operations. The three families are intersection (/=\), difference
    # (\=) and union (\=/), each in a unifying, an equal and an alpha variant.
    #
    # Six of the nine carry a MeTTa variable in an argument, and the call
    # answers the resulting term all the same.
    assert m.fn["/=\\"]((1, 2, V.a), (2, 3, 4)) == [Expression((2, 2))]
    assert m.fn["/==\\"]((1, 2, 3), (2, 3, 4)) == [Expression((2, 3))]
    unified = m.fn["/=a\\"]((1, 2, V.a), (2, V.a, 4)).one()
    assert unified.alpha_eq(Expression((2, V.a)))

    assert m.fn["\\="]((1, 2, 3), (V.a, 3, 4)) == [Expression((2,))]
    assert m.fn["\\=="]((1, 2, 3), (2, 3, 4)) == [Expression((1,))]
    assert m.fn["\\=a"]((1, 2, V.a), (2, V.a, 4)) == [Expression((1,))]

    assert m.fn["\\=/"]((1, 2, 3), (V.a, 3, 4)) == [Expression((2, 1, 3, 4))]
    assert m.fn["\\==/"]((1, 2, 3), (2, 3, 4)) == [Expression((1, 2, 3, 4))]
    joined = m.fn["\\=a/"]((1, 2, V.a), (2, V.a, 4)).one()
    assert joined.alpha_eq(Expression((1, 2, V.a, 4)))

    # Composition.
    assert m.fn["."](S.add(1), S.mul(2), 1) == [3]
    assert m.fn[".:"](S.add(1), S.add, 2, 3) == [6]
    assert m.fn["&&&"](S.add(2), S.mul(2), 1) == [Expression((3, 2))]

    # A branch that answers nothing prunes, so the fan-out keeps one answer.
    @m.define
    def mfail(x):  # noqa: ARG001  -- the branch answers nothing whatever it is given, which is what makes it prune
        yield from ()

    assert list(m.fn["&^&"](S.add(1), S.mfail(), 1)) == [2]

    # Reverse function matching, which is `solve`: the PATTERN wins its
    # variables from what the subject produces, so the call runs backwards and
    # the bindings come back projected by name.
    taken = m.solve(S["@"](V.lst, S.cons(V.h, V.t)), (1, 2, 3))
    assert (taken.lst, taken.h, taken.t) == (Expression((1, 2, 3)), 1, Expression((2, 3)))
    assert m.solve(S.head(V.x), (1, 2, 3)).x == 1
    assert m.solve(S.tail(V.xs), (1, 2, 3)).xs == Expression((2, 3))
    assert m.solve(S.mylast(V.x), (1, 2, 3)).x == 3
    assert m.solve(S.init(V.xs), (1, 2, 3)).xs == Expression((1, 2))
    split = m.solve(S.rcons(V.xs, V.x), (1, 2, 3))
    assert (split.xs, split.x) == (Expression((1, 2)), 3)

    # prog1 answers its first form, progn its last; both run both.
    assert m.fn.prog1(S.add(1, 1), S.add(2, 2)) == [2]
    assert m.fn.progn(S.add(1, 1), S.add(2, 2)) == [4]
