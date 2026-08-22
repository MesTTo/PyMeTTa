"""Purpose: examples/libraries/roman_test.metta in Python: lib_roman, walked end to end.

Every claim here is about a lib_roman function, so every one names it. Three
families: the higher-order maps and folds, the nine set operations whose names
are drawn from the shapes of their Venn diagrams, and the composition
combinators. Then the part Python has no spelling for at all, `let` unifying a
CALL against a value so the function runs BACKWARDS: `(let (head $x) (1 2 3)
$x)` answers 1 because head, run in reverse, says what its argument's first
element must be.

Two answers carry a fresh variable, which is why they are compared with
`alpha_eq` rather than `==`: the engine renames variables and the claim is
about the shape, not the name.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, alpha_eq

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 214065 to 207878, -6187 (-2.89%), by the idiomatic
#: rewrite: twenty-six `test` wrappers and two `collapse`s left the engine
#: for `assert` and `.all()`; the twenty-six library calls and the
#: specializations they trigger are the rest. Measured min-of-three with the
#: MORK backend linked into this worktree, which the earlier figure may not
#: have been. Prior: 214065 was the last figure for the generator twin that
#: yielded `m.eval(S.test(...))` once per runnable form.
BUDGET = 207878


def twin(m):
    """Import lib_roman, then exercise its three families and its inverses."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    # Higher-order functions.
    assert list(m.fn("map-flat")(S["+"](1), (1, 2, 3))) == [2, 3, 4]
    assert m.fn("map-nested")(S["+"](1), (1, (2, 3))) == Expression((2, Expression((3, 4))))
    assert m.fn("fold-flat")(S["+"], 0, (1, 2, 3)) == 6
    assert m.fn("foldr-flat")(S.cons, (), (1, (2, 3), 4)) == Expression((1, Expression((2, 3)), 4))
    assert m.fn("fold-nested")(S["+"], 0, (1, (2, 3))) == 6

    # Set operations. The three families are intersection (/=\), difference
    # (\=) and union (\=/), each in a unifying, an equal and an alpha variant.
    assert list(m.fn("/=\\")((1, 2, V.a), (2, 3, 4))) == [2, 2]
    assert list(m.fn("/==\\")((1, 2, 3), (2, 3, 4))) == [2, 3]
    assert alpha_eq(m.fn("/=a\\")((1, 2, V.a), (2, V.a, 4)), Expression((2, V.a)))

    assert list(m.fn("\\=")((1, 2, 3), (V.a, 3, 4))) == [2]
    assert list(m.fn("\\==")((1, 2, 3), (2, 3, 4))) == [1]
    assert list(m.fn("\\=a")((1, 2, V.a), (2, V.a, 4))) == [1]

    assert list(m.fn("\\=/")((1, 2, 3), (V.a, 3, 4))) == [2, 1, 3, 4]
    assert list(m.fn("\\==/")((1, 2, 3), (2, 3, 4))) == [1, 2, 3, 4]
    assert alpha_eq(m.fn("\\=a/")((1, 2, V.a), (2, V.a, 4)), Expression((1, 2, V.a, 4)))

    # Composition.
    assert m.fn(".")(S["+"](1), S["*"](2), 1) == 3
    assert m.fn(".:")(S["+"](1), S["+"], 2, 3) == 6
    assert list(m.fn("&&&")(S["+"](2), S["*"](2), 1)) == [3, 2]

    # A branch that answers nothing prunes, so the fan-out keeps one answer.
    @m.define
    def mfail(x):  # noqa: ARG001  -- the branch answers nothing whatever it is given, which is what makes it prune
        yield from ()

    assert m.fn("&^&").all(S["+"](1), S.mfail(), 1) == [2]

    # Reverse function matching, the part with no Python spelling at all.
    assert m.one(S.let(S["@"](V.lst, S.cons(V.h, V.t)), (1, 2, 3), Expression((V.lst, V.h, V.t)))) == Expression((Expression((1, 2, 3)), 1, Expression((2, 3))))  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.one(S.let(S.head(V.x), (1, 2, 3), V.x)) == 1  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.one(S.let(S.tail(V.xs), (1, 2, 3), V.xs)) == Expression((2, 3))  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.one(S.let(S.mylast(V.x), (1, 2, 3), V.x)) == 3  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.one(S.let(S.init(V.xs), (1, 2, 3), V.xs)) == Expression((1, 2))  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do
    assert m.one(S.let(S.rcons(V.xs, V.x), (1, 2, 3), Expression((V.xs, V.x)))) == Expression((Expression((1, 2)), 3))  # rung: reverse function matching: `let` unifies a CALL against a value and runs the function backwards, which Python's assignment cannot do

    # prog1 answers its first form, progn its last; both run both.
    assert m.fn("prog1")(S["+"](1, 1), S["+"](2, 2)) == 2
    assert m.fn("progn")(S["+"](1, 1), S["+"](2, 2)) == 4
