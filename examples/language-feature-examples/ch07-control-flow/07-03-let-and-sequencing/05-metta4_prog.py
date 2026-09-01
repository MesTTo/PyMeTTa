"""Purpose: examples/ch07-control-flow/07-03-let-and-sequencing/05-metta4_prog.metta in Python: sequencing.

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
    assert m[S.friend(S.sam, V.who)].who == [S.tim]

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
#: RE-PINNED 2026-09-01, 582 to 639 (+57), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 639 to 713 (+74), the subtract-atom primitive and the
#: Counter grain for -=: a new engine head shifts every twin's load structure,
#: and the removal doors changed meaning where a twin spells one [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 713 to 630 (-83), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 630 to 635 (+5), generic Python operators now dispatch
#: through live protocols while source twins explicitly name relational engine
#: heads [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 635
