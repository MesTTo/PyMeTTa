"""Purpose: examples/data/holfunctions.metta in Python: the higher-order forms.

`map-atom`, `filter-atom` and `foldl-atom` take a TEMPLATE or a function and
walk an expression with it. Python has all three in its own syntax, and the
compiler emits exactly those instructions: a list comprehension over a tuple
compiles to `map-atom`, adding an `if` compiles to `filter-atom` inside it, and
`sum` compiles to `foldl-atom` with `+`. So the `a` half of this file is
written as ordinary comprehensions and reads as ordinary Python, while the
engine sees the instructions the original wrote by hand.

The `b` half passes a NAMED function instead of a template, and three of those
four are the same comprehension calling the function. `f1b` folds with a named
function, which Python's own `functools.reduce` would spell out here but a
compiled body has no name for, so that clause is written as the term it is.

Every one of these definitions is nullary, so each has exactly one clause and
no stacking question arises.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 16462 to 19082, +2620 (+15.92%), by the twin-shape
#: rewrite: two moves in opposite directions, both measured. Six `test`
#: wrappers left the engine for `assert`, worth about 3,700; and five
#: definitions ENTERED the compiler, because a list comprehension is what
#: `map-atom` and `filter-atom` are for and `sum` is what `foldl-atom` is
#: for, so `f1a`, `f2a`, `f3a`, `f2b` and `f3b` are ordinary Python bodies
#: rather than stored terms. The same file with those five written at the
#: container door measures 12755, so compiling them costs 6,327 once per
#: process and nothing per call. Against the example's 23325 the ratio is
#: 0.8181 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/holfunctions.metta`]. Prior: RE-PINNED at 16462 by the
#: wave-4 idiom rewrite.
BUDGET = 19082


def twin(m):
    """Fold, map and filter, first with templates and then with names."""

    @m.define
    def foldfun(a, b):
        return a + b

    @m.define
    def mapfun(a):
        return a + 1

    @m.define
    def filterfun(x):
        return x > 3

    @m.define
    def f1a():
        return sum((1, 2, 3, 4))

    @m.define
    def f2a():
        return [x + 1 for x in (1, 2, 3)]

    @m.define
    def f3a():
        return [x for x in (1, 2, 3, 4, 5) if x > 3]

    m += equation(S.f1b()).to(S["foldl-atom"](Expression((1, 2, 3, 4)), 0, S.foldfun))  # rung: folding with a NAMED function is functools.reduce, which a compiled body cannot name (P14.4)

    @m.define
    def f2b():
        return [mapfun(x) for x in (1, 2, 3)]

    @m.define
    def f3b():
        return [x for x in (1, 2, 3, 4, 5) if filterfun(x)]

    @m.define
    def foldfun2(a, b):
        return append(a, b)  # noqa: F821  -- append is an engine function, resolved by name in a compiled body

    assert m.fn("f1a")() == 10
    assert m.fn("f2a")() == Expression((2, 3, 4))
    assert m.fn("f3a")() == Expression((4, 5))

    assert m.fn("f1b")() == 10
    assert m.fn("f2b")() == Expression((2, 3, 4))
    assert m.fn("f3b")() == Expression((4, 5))

    # The template variant of the same fold, appending expressions rather than
    # adding numbers.
    joined = S["foldl-atom"](Expression((Expression((1, 2)), Expression((3, 4)), Expression((5, 6)))), Expression(()), V.acc, V.x, S.append(V.acc, V.x))  # rung: a fold whose template BINDS its own variables has no Python binding position at all (P14.4)
    assert m.eval(joined) == [Expression((1, 2, 3, 4, 5, 6))]
