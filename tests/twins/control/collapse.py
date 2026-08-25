"""Purpose: examples/control/collapse.metta in Python: collapsing one answer.

`(1 2 3)` has no head to call, so it answers itself, and `collapse` gathers
that one answer into a one-element expression. The doubled parentheses of
`((1 2 3))` are the whole point of the file, and in Python they are a list
holding one atom: evaluating a term already answers the multiset, so
`collapse` needs no spelling of its own.
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
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 227 to 228, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
BUDGET = 228


def twin(m):
    """Evaluate a term nothing reduces, and count the answers it gives."""
    # !(test (collapse (1 2 3)) ((1 2 3)))
    assert m.eval(Expression((1, 2, 3))) == [Expression((1, 2, 3))]
