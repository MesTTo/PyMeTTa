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

from petta import S, V

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


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
