"""Purpose: examples/control/case2.metta in Python: a branch may fork.

One branch, whose pattern is the key itself so everything reaches it, and
whose VALUE is a superposition: a `case` answers whatever its branch answers,
which is two things here. The `case` therefore decides nothing, and what is
left is the fork, which a generator's two yields say directly.

Both tags are lowercase symbols reached through the `S` factory, which a
compiled body reads as the atom it builds rather than as a function to call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """One head, one branch, two answers."""
    @m.define(name="compile")
    def compiled(_stmt):
        # (= (compile $stmt) (case $stmt (($stmt (superpose (what what2))))))
        yield S.what
        yield S.what2

    # !(test (collapse (compile wat)) (what what2))
    assert compiled(S.wat) == [S.what, S.what2]
