"""examples/control/metta4_prog.metta in Python: sequencing.

`progn` runs its forms in order and answers the last one, which is exactly
what a sequence of Python statements already is, so the first form's four
engine calls become four ordinary lines: two writes, one removal and one
query, each through the door the dissolution table names for it.

`prog1` runs every form and answers the FIRST. Python has no statement whose
value is the first of several, and over three constants there are no
statements to write at all, so the last two forms stay terms.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1807 to 639, -1168 (-64.6%), by the twin contract
#: change: the whole first form LEFT the engine: `progn`'s two writes, its
#: removal and its match became `+=`, `-=` and the query door, which is what
#: a statement sequence already is, and three `test` wrappers became
#: `assert`s. Measured min-of-3 over fresh processes with the MORK backend
#: linked in, which the artefact-free worktree omits and which moves a
#: compiled twin by about 10 inferences per definition; against the example's
#: 4660 the ratio is 0.1371. Prior: 1807, the transliterated twin this
#: replaces.
BUDGET = 639


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
    assert m.query(S.friend(S.sam, V.who))["who"] == [S.tim]

    # !(test (prog1 1 2 3) 1)
    # rung: `prog1` answers its first form after running the rest, and Python has no statement whose value is the first of several
    assert m.eval(S.prog1(1, 2, 3)) == [1]

    # !(test (progn 1 2 3) 3)
    # rung: a statement sequence IS progn, and three constants are no statements
    assert m.eval(S.progn(1, 2, 3)) == [3]
