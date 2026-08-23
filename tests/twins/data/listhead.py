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

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Unpack an expression, then count one the long way and the short way."""
    m += equation(S.len(Expression(()))).to(0)
    m += equation(S.len(S.cons(V.head, V.tail))).to(S.len(V.tail) + 1)

    head, *tail = Expression((1, 2, 3, 4, 5, 6))
    counted = Expression((1, 2, 3))

    assert (head, tail) == (1, [2, 3, 4, 5, 6])
    assert m.fn.len(counted).one() == len(counted) == 3
    assert m.fn.cons(42, Expression(())).one() == Expression((42,))
