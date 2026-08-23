"""Purpose: examples/control/if3.metta in Python: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs, which is itself an `if`.

Both `if`s are Python conditional expressions and the condition is
`fn.is_var(x)`, so the file compiles whole. `lol` is `S.lol`, the lowercase
symbol reached through the factory, which a compiled body reads as the atom it
builds rather than as a function to call.

`chosen(V.A)` passes a variable as DATA, which is what the example does, and
the answer is 42. Measured 2026-08-23: the same call outside a `stats()` scope
answers `[Row(A=$_70)]` instead, because the answer view reads any caller
variable as a binding to report. A twin runs inside a stats scope, so this
file is written for the door's behaviour there; the divergence is the
library's to fix.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Ask whether a variable is a variable, and take the arm that answers."""
    @m.define
    def chosen(x):
        # (if (is-var $x) (if True 42 lol) (+ 2 2))
        return (42 if True else S.lol) if fn.is_var(x) else 2 + 2

    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    assert chosen(V.A) == [42]
