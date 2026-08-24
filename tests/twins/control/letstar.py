"""Purpose: examples/control/letstar.metta in Python: sequential bindings.

Inside a compiled body `x = 1` IS a `let*` binding: the decorator folds a
statement list into nested bindings around what follows it, so the Python for
this file is three lines of ordinary function body and the equation stored is
`(let* (($x 1)) (let* (($y 2)) (+ $x $y)))`, the same nesting the source
writes flat.
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
    """Bind two names in order, then add them."""
    @m.define
    def summed():
        # (let* (($x 1) ($y 2)) (+ $x $y))
        x = 1
        y = 2
        return x + y

    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    assert summed() == [3]
