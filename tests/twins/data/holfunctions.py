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

A compiled definition is called by its Python name, which is what makes the
claims read as ordinary calls; `f1b` has no Python name because it is a stored
equation, so it is reached through the function namespace instead.

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

from metta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


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

    m += equation(S.f1b()).to(S.foldl_atom(Expression((1, 2, 3, 4)), 0, S.foldfun))  # rung: folding with a NAMED function is functools.reduce, which a compiled body cannot name (P14.4)

    @m.define
    def f2b():
        return [mapfun(x) for x in (1, 2, 3)]

    @m.define
    def f3b():
        return [x for x in (1, 2, 3, 4, 5) if filterfun(x)]

    @m.define
    def foldfun2(a, b):
        return append(a, b)  # noqa: F821  -- append is an engine function, resolved by name in a compiled body

    assert f1a().one() == 10
    assert f2a().one() == Expression((2, 3, 4))
    assert f3a().one() == Expression((4, 5))

    assert m.fn.f1b().one() == 10
    assert f2b().one() == Expression((2, 3, 4))
    assert f3b().one() == Expression((4, 5))

    # The template variant of the same fold, appending expressions rather than
    # adding numbers. A template BINDS its own variables inside the call, which
    # is not a Python binding position at all (P14.4).
    parts = Expression((Expression((1, 2)), Expression((3, 4)), Expression((5, 6))))
    joined = S.foldl_atom(parts, Expression(()), V.acc, V.x, S.append(V.acc, V.x))
    assert m.eval(joined) == [Expression((1, 2, 3, 4, 5, 6))]
