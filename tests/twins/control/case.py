"""Purpose: examples/control/case.metta in Python: the first matching branch.

The key 5 misses the literal branch 4 and meets the first variable pattern, so
the answer is 44 and the third branch never runs at all.

A `case` IS Python's `match` statement, and the compiled subset lowers one to
the other: a literal arm beside a catch-all is the shape the guide's own `rate`
exemplar writes, and the equation stored is the case tower the source writes
flat. The third branch has no Python spelling and needs none, because Python
refuses a second irrefutable arm outright, which is the language saying what
the comment on the original says.
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
        match x:
            case 4:
                return 42
            case _:
                return 44

    # !(test (casetest 5) 44)
    assert casetest(5) == [44]
