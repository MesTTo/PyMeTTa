"""Purpose: examples/control/case.metta in Python: the first matching branch.

The key 5 misses the literal branch 4 and meets the first variable pattern, so
the answer is 44 and the third branch never runs at all.

Two branches, one a literal and one matching anything, is a two-way question
about the key, and Python's conditional expression asks it. The third branch is
unreachable in either spelling. What is NOT reachable is a `case` whose
branches are PATTERNS over structure: Python's `match` statement has no
lowering in the compiled subset yet, which the residue table records against
P14.4, and this file's `case` happens not to need one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Dispatch on a key that misses the literal branch."""
    @m.define
    def casetest(x):
        # (= (casetest $x) (case $x ((4 42) ($otherpattern 44) ($otherother $45))))
        return 42 if x == 4 else 44

    # !(test (casetest 5) 44)
    assert casetest(5) == [44]
