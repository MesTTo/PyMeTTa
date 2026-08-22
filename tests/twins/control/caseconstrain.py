"""Purpose: examples/control/caseconstrain.metta in Python: destructuring an expression.

The example asks MeTTa's `case` to match `(1 2 3)` against the cons constraint
`(cons $h $t)` and answer the head, which is 1. Python's own unpacking says
that directly, because an expression is a sequence: `head, *tail = e`
binds the head to the first child and the tail to the rest, at no engine cost
at all, which is what the ladder means by a structure operation on an atom
already held in Python.

What is NOT reachable is MeTTa's `case` itself. Python's match statement has no
lowering in the compiled subset yet, so no twin can put this example's own
construct into the engine; that is filed as residue against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression

#: Inferences this twin spends, its own tripwire.
BUDGET = 5


def twin(m):  # noqa: ARG001  -- the engine is unreachable here: MeTTa's `case` has no compiled Python spelling, and the destructuring it demonstrates is native Python (residue, P14.4)
    """Take the head of an expression, the way Python takes it."""
    # (case (1 2 3) (((cons $h $t) $h)))
    head, *tail = Expression((1, 2, 3))
    assert head == 1
    assert tail == [2, 3]
