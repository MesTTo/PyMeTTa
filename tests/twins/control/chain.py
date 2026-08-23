"""Purpose: examples/control/chain.metta in Python: `chain` names its result.

`(chain expr $n body)` runs `expr`, binds the answer to a name, and runs the
body with that name in scope. Python spells that with an ordinary assignment
statement, and a second assignment nests inside the first exactly as a second
`chain` nests inside the first, which is what `summed` below reads like.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Name one intermediate result, then two."""
    @m.define
    def scaled():
        # (chain (+ 2 4) $n (* 3 $n))
        n = 2 + 4
        return 3 * n

    # !(test (chain (+ 2 4) $n (* 3 $n)) 18)
    assert scaled() == [18]

    @m.define
    def summed():
        # (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m)))
        n = 1 + 3
        doubled = 2 * n
        return n + doubled

    # !(test (chain (+ 1 3) $n (chain (* 2 $n) $m (+ $n $m))) 12)
    assert summed() == [12]
