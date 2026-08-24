"""Purpose: examples/control/if.metta in Python: the three-argument `if`.

Both arms are expressions, `(3 4)` and `(5 6)`, and a Python tuple is one. The
condition is false, so the answer is the second arm.

Inside a compiled body Python's own conditional expression IS this form:
`(3, 4) if 1 > 2 else (5, 6)` lowers to `(if (> 1 2) (3 4) (5 6))` arm for arm,
and the arm that is not taken is never evaluated on either side.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Ask a false question and read the arm it takes."""
    @m.define
    def pick():
        # (if (> 1 2) (3 4) (5 6))
        return (3, 4) if 1 > 2 else (5, 6)  # noqa: PLR0133  -- comparing two constants is the example's own program: the engine reduces `(> 1 2)`, and folding it in Python would leave the `if` nothing to decide

    # !(test (if (> 1 2) (3 4) (5 6)) (5 6))
    assert pick() == [Expression((5, 6))]
