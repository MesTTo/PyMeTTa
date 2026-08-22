"""Purpose: examples/control/if.metta in Python: the three-argument `if`.

Both arms are expressions, `(3 4)` and `(5 6)`, and a Python tuple is one. The
condition is false, so the answer is the second arm.

Inside a compiled body Python's own conditional expression IS this form:
`(3, 4) if 1 > 2 else (5, 6)` lowers to `(if (> 1 2) (3 4) (5 6))` arm for arm,
and the arm that is not taken is never evaluated on either side. This file used
to say that in a comment and write the term instead, because a single
`@m.define` cost more than the band allowed an example this small; the band now
pays for authoring a definition, so the sentence and the code agree.
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
#: RE-PINNED 2026-08-22, 654 to 2861, +2207 (+337.5%), by lifting this twin
#: to the definitional door now that the band pays for authoring: the `if`
#: ENTERED the engine as a compiled Python conditional expression, where the
#: twin used to state the term. The whole of the increase is `@m.define`'s
#: authoring cost, which the band now allows because the example it prices
#: against has no definition to author; the equation stored and the clauses
#: compiled are what the example's own `if` compiles to, so the RUNNING cost
#: did not move. Measured min-of-3 over fresh processes with the MORK backend
#: linked in; against the example's 2092 the ratio is 1.3676, and the ceiling
#: is 4522, the example plus 10% plus 2221 to author 1 definition. Prior:
#: 654, the term-door twin the old band forced.
BUDGET = 2861


def twin(m):
    """Ask a false question and read the arm it takes."""
    @m.define
    def pick():
        # (if (> 1 2) (3 4) (5 6))
        return (3, 4) if 1 > 2 else (5, 6)  # noqa: PLR0133  -- comparing two constants is the example's own program: the engine reduces `(> 1 2)`, and folding it in Python would leave the `if` nothing to decide

    # !(test (if (> 1 2) (3 4) (5 6)) (5 6))
    assert pick() == [Expression((5, 6))]
