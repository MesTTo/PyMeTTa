"""Purpose: examples/control/if2.metta in Python: a symbol is not a variable.

`(is-var a)` asks about the ATOM `a`, so the answer is False and the else arm
runs. The then arm `(() (+ 1 1))` is an expression whose first element is the
empty expression, and Python's own empty tuple is that atom.

The whole form is one compiled equation. The `if` is Python's conditional
expression and the condition is `fn.is_var(x)`: the function namespace is a
builder a compiled body reads by lexical identity, so rung 4's
underscore-to-hyphen map reaches `is-var` without the twin ever writing the
name as text.

One lowering worth naming: a test position that is not already boolean by its
syntax wraps in `py-truthy`, so the equation stored is
`(if (py-truthy (is-var $x)) (() (+ 1 1)) (+ 2 2))`. That is Python's own rule
for what counts as true, made explicit rather than assumed.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Ask whether a symbol is a variable, and take the arm that answers."""
    @m.define
    def branch(x):
        # (if (is-var $x) (() (+ 1 1)) (+ 2 2))
        return ((), 1 + 1) if fn.is_var(x) else 2 + 2

    # !(test (if (is-var a) (() (+ 1 1)) (+ 2 2)) 4)
    assert branch(S.a) == [4]
