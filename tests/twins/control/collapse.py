"""Purpose: examples/control/collapse.metta in Python: collapsing one answer.

`(1 2 3)` has no head to call, so it answers itself, and `collapse` gathers
that one answer into a one-element expression. The doubled parentheses of
`((1 2 3))` are the whole point of the file, and in Python they are a list
holding one atom: evaluating a term already answers the multiset, so
`collapse` needs no spelling of its own.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Evaluate a term nothing reduces, and count the answers it gives."""
    # !(test (collapse (1 2 3)) ((1 2 3)))
    assert m.eval(Expression((1, 2, 3))) == [Expression((1, 2, 3))]
