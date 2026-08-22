"""Purpose: examples/data/holfunctions_intrinsicop.metta in Python: a builtin, partially applied.

`mymap` is written out rather than borrowed: two clauses, one for the empty
expression and one for a cons cell, walking the structure and rebuilding it.
Both select on SHAPE in the head, which a compiled parameter list cannot spell,
so they are written as the equations they are.

The claim is that a builtin and a defined function behave the same when either
is handed to `mymap` half-applied. `(== 1)` is `==` with one argument, `(eq 1)`
is the same for a function whose body IS `==`, and mapping either over
`(1 2 3)` answers `(True False False)`. The specializer sees both and compiles
a clause for each, which is what makes the comparison worth making.

`eq` is written as an equation rather than as `def eq(a, b): return a == b`,
and the reason is the claim itself: Python's `==` in a compiled body lowers to
`(py-eq $a $b)`, a crossing to the host per comparison, not to MeTTa's own
`==` (measured; filed as P14.24). Comparing a builtin against a host crossing
would be a different claim from the one the example makes. `a > b` in the same
position DOES lower to MeTTa's `>`, so this is one operator, not the family.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10337 to 10353, +16 (+0.15%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`, and nothing else
#: moved: the two structural clauses, `eq`, and the two half-applied maps are
#: the same atoms the original writes. Writing `eq` as `def eq(a, b): return
#: a == b` instead measures 12020, and the extra 1,667 is the compiler's one-
#: time warm-up for the first compiled definition in a process, which buys a
#: clause that lowers to `(py-eq $a $b)` rather than to the `==` this example
#: is about. Against the example's 13372 the ratio is 0.7742 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/holfunctions_intrinsicop.metta`]. Prior: the file's first
#: pin, uncommented.
BUDGET = 10353


def twin(m):
    """Map a partially applied builtin and its defined twin over one list."""
    m += equation(S.mymap(V.f, Expression(()))).to(Expression(()))
    m += equation(S.mymap(V.f, S.cons(V.x, V.xs))).to(
        S.cons(Expression((V.f, V.x)), S.mymap(V.f, V.xs))
    )

    m += equation(S.eq(V.a, V.b)).to(V.a.eq(V.b))

    numbers = Expression((1, 2, 3))
    assert m.fn("mymap").all(S["=="](1), numbers) == m.fn("mymap").all(S.eq(1), numbers)
