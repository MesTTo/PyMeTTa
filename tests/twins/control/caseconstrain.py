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
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):  # noqa: ARG001  -- the engine is unreachable here: MeTTa's `case` has no compiled Python spelling, and the destructuring it demonstrates is native Python (residue, P14.4)
    """Take the head of an expression, the way Python takes it."""
    # The top rung puts the example's own `case` into the engine:
    #
    #     @m.define
    #     def head_of(e):
    #         match e:
    #             case (h, *_):
    #                 return h
    #
    # `ast.Match` has no lowering in the compiled subset, so no twin can put
    # this construct into the engine at all and the destructuring below is
    # what is left. Residue: P14.4.
    # (case (1 2 3) (((cons $h $t) $h)))
    head, *tail = Expression((1, 2, 3))
    assert head == 1
    assert tail == [2, 3]
