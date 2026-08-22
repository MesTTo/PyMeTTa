"""Purpose: examples/data/listhead.metta in Python: list structure, twice over.

`(cons $Head $Tail)` is how MeTTa takes an expression apart, and `head, *tail =
e` is how Python does, at no engine cost at all: the first claim is that
unpacking, written directly. The recursive `len` is the other half, and it is
written as equations for two reasons that both matter: its clauses select on
`()` and on a cons cell, which a compiled parameter list cannot spell, and its
name is Python's own builtin.

That name is the interesting part. The engine walks the structure clause by
clause and Python's `len` reads the count off the expression, and the third
claim says they agree.
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
#: RE-PINNED 2026-08-22, 4655 to 3099, -1556 (-33.43%), by the twin-shape
#: rewrite: three `test` wrappers left the engine for `assert`, and the cons-
#: pattern claim became `head, *tail = e`, which is native. The recursive
#: `len` still walks in the engine, and the claim now says it agrees with
#: Python's `len`. Against the example's 8323 the ratio is 0.3723 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/listhead.metta`]. Prior: the file's first pin, uncommented.
BUDGET = 3099


def twin(m):
    """Unpack an expression, then count one the long way and the short way."""
    m += equation(S.len(Expression(()))).to(0)
    m += equation(S.len(S.cons(V.head, V.tail))).to(S.len(V.tail) + 1)

    head, *tail = Expression((1, 2, 3, 4, 5, 6))
    assert (head, tail) == (1, [2, 3, 4, 5, 6])
    assert m.fn("len")(Expression((1, 2, 3))) == len(Expression((1, 2, 3))) == 3
    assert m.fn("cons")(42, Expression(())) == Expression((42,))
