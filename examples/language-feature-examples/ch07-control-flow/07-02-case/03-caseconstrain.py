"""Purpose: examples/ch07-control-flow/07-02-case/03-caseconstrain.metta in Python: destructuring an expression.

The example asks MeTTa's `case` to match `(1 2 3)` against the cons constraint
`(cons $h $t)` and answer the head, which is 1. Python's own unpacking says
that directly, because an expression is a sequence: `head, *tail = e` binds the
head to the first child and the tail to the rest, at no engine cost at all,
which is what the ladder means by a structure operation on an atom already held
in Python, and what the guide's structure family lists as `decons-atom`.

The example's own `case` is now half reachable. `ast.Match` lowers, so a case
whose branches are patterns over structure compiles; what refuses is the STAR
in `case (h, *tail)`, which needs the engine's named segment variables:
"star patterns need the engine's named segment variables; spell the fixed
prefix today and use that segment-variable row when it lands"
[measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. A fixed-arity arm, `case (h, _b, _c)`,
does compile, and it is a NARROWER claim than the original's cons pattern,
which holds for a tail of any length. So the destructuring below stays, and the
star arm is filed against P14.4 with P4.10, the sequence-variable row, as its
prerequisite.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression


def twin(m):  # noqa: ARG001  -- the engine is unreachable here: the example's cons pattern needs a star arm, which the compiled subset refuses, and the destructuring it demonstrates is native Python (residue, P14.4)
    """Take the head of an expression, the way Python takes it."""
    # The top rung puts the example's own `case` into the engine:
    #
    #     @m.define
    #     def head_of(e):
    #         match e:
    #             case (h, *_tail):
    #                 return h
    #
    # The statement lowers, the star arm does not: it needs the engine's
    # named segment variables. Residue: P14.4, behind P4.10.
    # (case (1 2 3) (((cons $h $t) $h)))
    head, *tail = Expression((1, 2, 3))
    assert head == 1
    assert tail == [2, 3]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
BUDGET = 5
