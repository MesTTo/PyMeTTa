"""Purpose: examples/control/if3.metta in Python: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs, which is itself an `if`.

Both `if`s are Python conditional expressions and the condition is
`fn.is_var(x)`, so the file compiles whole. `lol` is `S.lol`, the lowercase
symbol reached through the factory, which a compiled body reads as the atom it
builds rather than as a function to call.

`chosen(V.A)` passes a variable as DATA, which is what the example does, and
the answer is 42. A twin runs inside a `stats()` scope and the call answers the
same either way, so nothing here depends on the scope; an earlier note in this
file said the two doors diverged and they no longer do
[re-measured 2026-08-24: `chosen(V.A)` answers `[42]` both inside and outside
`m.stats()`; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Ask whether a variable is a variable, and take the arm that answers."""
    @m.define
    def chosen(x):
        # (if (is-var $x) (if True 42 lol) (+ 2 2))
        return (42 if True else S.lol) if fn.is_var(x) else 2 + 2

    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    assert chosen(V.A) == [42]
