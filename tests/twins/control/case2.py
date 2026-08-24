"""Purpose: examples/control/case2.metta in Python: a branch may fork.

One branch, whose pattern is the key itself so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here. The `case` therefore decides nothing, and what is
left is the fork.

The fork is `superpose(...)`, the expression-position door, and not two
yields. They are different knowledge: two yields store TWO equations where the
example stores ONE whose body superposes, and `match` sees one atom rather than
two. Both tags are lowercase symbols reached through the `S` factory, which a
compiled body reads as the atom it builds rather than as a function to call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, superpose

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """One head, one branch, two answers."""
    # The def's own name IS the head, so `name=` is for heads Python cannot
    # spell, and `compile` is one of them HERE: the identifier shadows a
    # builtin, which this repository's gate refuses by budget rather than by
    # taste (the A family's burn-down maximum is 8 and is full), so writing
    # `def compile` would cost a suppression the gate does not have
    # [measured 2026-08-24: `GATE_ONLY=1 sh check.sh` failed with
    # "P0.13 suppression burn-down increased (observed, maximum): {'A': (9, 8)}";
    # commit=WORKTREE].
    @m.define(name="compile")
    def compiled(_stmt):
        # (= (compile $stmt) (case $stmt (($stmt (superpose (what what2))))))
        return superpose(S.what, S.what2)

    # !(test (collapse (compile wat)) (what what2))
    assert compiled(S.wat) == [S.what, S.what2]
