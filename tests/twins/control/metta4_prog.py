"""Purpose: examples/control/metta4_prog.metta in Python: sequencing.

`progn` runs its forms in order and answers the last one, which is exactly
what a sequence of Python statements already is, so the first form's four
engine calls become four ordinary lines: two writes, one removal and one
query, each through the door the dissolution table names for it.

`prog1` runs every form and answers the FIRST. Python has no statement whose
value is the first of several, and over three constants there are no
statements to write at all, so the last two forms stay terms.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V


def twin(m):
    """Write a fact, take it back, write another, and read what is left."""
    # !(test (progn (add-atom &self (friend sam tom))
    #               (remove-atom &self (friend sam tom))
    #               (add-atom &self (friend sam tim))
    #               (match &self (friend sam $1) $1))
    #        tim)
    m += S.friend(S.sam, S.tom)
    m -= S.friend(S.sam, S.tom)
    m += S.friend(S.sam, S.tim)
    assert m.match(S.friend(S.sam, V.who)).who == [S.tim]

    # The top rung is a statement sequence whose value is the FIRST statement.
    # Python has none: `progn` is what a statement sequence already is, and the
    # first form above is written as one, but three constants are no statements
    # and `prog1` answers the first form after running the rest.
    # !(test (prog1 1 2 3) 1)
    # rung: `prog1` answers its first form after running the rest, and Python has no statement whose value is the first of several
    assert m.eval(S.prog1(1, 2, 3)) == [1]

    # !(test (progn 1 2 3) 3)
    # rung: a statement sequence IS progn, and three constants are no statements
    assert m.eval(S.progn(1, 2, 3)) == [3]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 579 to 580, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 580 to 582, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 582
