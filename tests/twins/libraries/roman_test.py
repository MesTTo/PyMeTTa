"""Purpose: examples/libraries/roman_test.metta in Python: lib_roman, walked end to end.

Every claim here is about a lib_roman function, so every one names it. Three
families: the higher-order maps and folds, the nine set operations whose names
are drawn from the shapes of their Venn diagrams, and the composition
combinators. Then the inverses: `let` unifying a CALL against a value so the
function runs BACKWARDS, where `(let (head $x) (1 2 3) $x)` answers 1 because
head, run in reverse, says what its argument's first element must be. `solve`
is the door the guide names for that shape, and the note beside those six
claims says why it cannot serve them yet.

The set operations are the family that carries VARIABLES in its arguments, so
they are stated as the terms they are; the note above them says why. Two of
their answers carry a fresh variable, which is why those are compared with
`alpha_eq` rather than `==`: the engine renames variables and the claim is
about the shape, not the name.

An engine function may be named with an ampersand, and three of these are:
`&&&`, `&^&` and the Venn family's punctuation take the bracket, which is the
exact door for a name Python's grammar cannot spell.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Import lib_roman, then exercise its three families and its inverses."""
    m.eval(S["import!"](m, S.library(S["lib_roman"])))

    # Higher-order functions.
    assert m.fn.map_flat(S["+"](1), (1, 2, 3)) == [Expression((2, 3, 4))]
    assert m.fn.map_nested(S["+"](1), (1, (2, 3))) == [
        Expression((2, Expression((3, 4))))
    ]
    assert m.fn.fold_flat(S["+"], 0, (1, 2, 3)) == [6]
    assert m.fn.foldr_flat(S.cons, (), (1, (2, 3), 4)) == [
        Expression((1, Expression((2, 3)), 4))
    ]
    assert m.fn.fold_nested(S["+"], 0, (1, (2, 3))) == [6]

    # Set operations. The three families are intersection (/=\), difference
    # (\=) and union (\=/), each in a unifying, an equal and an alpha variant.
    #
    # DEFECT, and this is what it costs the family. Every line below ought to
    # read `m.fn["/=\\"](...)`, the call door. Six of the nine carry a MeTTa
    # variable in an argument, and the answer view reads every variable in a
    # call as one of the caller's own and answers a binding row instead of the
    # term the claim is about. The family is stated through `eval` as one unit
    # rather than split by whether a given line happens to be ground.
    assert m.eval(S["/=\\"]((1, 2, V.a), (2, 3, 4))) == [Expression((2, 2))]
    assert m.eval(S["/==\\"]((1, 2, 3), (2, 3, 4))) == [Expression((2, 3))]
    [unified] = m.eval(S["/=a\\"]((1, 2, V.a), (2, V.a, 4)))
    assert unified.alpha_eq(Expression((2, V.a)))

    assert m.eval(S["\\="]((1, 2, 3), (V.a, 3, 4))) == [Expression((2,))]
    assert m.eval(S["\\=="]((1, 2, 3), (2, 3, 4))) == [Expression((1,))]
    assert m.eval(S["\\=a"]((1, 2, V.a), (2, V.a, 4))) == [Expression((1,))]

    assert m.eval(S["\\=/"]((1, 2, 3), (V.a, 3, 4))) == [Expression((2, 1, 3, 4))]
    assert m.eval(S["\\==/"]((1, 2, 3), (2, 3, 4))) == [Expression((1, 2, 3, 4))]
    [joined] = m.eval(S["\\=a/"]((1, 2, V.a), (2, V.a, 4)))
    assert joined.alpha_eq(Expression((1, 2, V.a, 4)))

    # Composition.
    assert m.fn["."](S["+"](1), S["*"](2), 1) == [3]
    assert m.fn[".:"](S["+"](1), S["+"], 2, 3) == [6]
    assert m.fn["&&&"](S["+"](2), S["*"](2), 1) == [Expression((3, 2))]

    # A branch that answers nothing prunes, so the fan-out keeps one answer.
    @m.define
    def mfail(x):  # noqa: ARG001  -- the branch answers nothing whatever it is given, which is what makes it prune
        yield from ()

    assert list(m.fn["&^&"](S["+"](1), S.mfail(), 1)) == [2]

    # Reverse function matching.
    #
    # DEFECT, and these six lines are what it costs. Each ought to read
    # `m.solve(S.head(V.x), (1, 2, 3)).x == [1]`, the door the guide names for
    # exactly this shape: the pattern must WIN its variables from what the
    # subject produces. `Space.solve` refuses that reading with "solve needs at
    # least one variable in its subject", so it serves only the guide's other
    # exemplar, `solve(4, V.x - 1).x`, where the variables sit on the subject
    # side and which answers 5 here. Until both readings land, `let` is written
    # as the term it is.
    assert m.eval(S.let(S["@"](V.lst, S.cons(V.h, V.t)), (1, 2, 3), Expression((V.lst, V.h, V.t)))) == [Expression((Expression((1, 2, 3)), 1, Expression((2, 3))))]  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.eval(S.let(S.head(V.x), (1, 2, 3), V.x)) == [1]  # rung: reverse function matching, as above
    assert m.eval(S.let(S.tail(V.xs), (1, 2, 3), V.xs)) == [Expression((2, 3))]  # rung: reverse function matching, as above
    assert m.eval(S.let(S.mylast(V.x), (1, 2, 3), V.x)) == [3]  # rung: reverse function matching, as above
    assert m.eval(S.let(S.init(V.xs), (1, 2, 3), V.xs)) == [Expression((1, 2))]  # rung: reverse function matching, as above
    assert m.eval(S.let(S.rcons(V.xs, V.x), (1, 2, 3), Expression((V.xs, V.x)))) == [Expression((Expression((1, 2)), 3))]  # rung: reverse function matching, as above

    # prog1 answers its first form, progn its last; both run both.
    assert m.fn.prog1(S["+"](1, 1), S["+"](2, 2)) == [2]
    assert m.fn.progn(S["+"](1, 1), S["+"](2, 2)) == [4]
