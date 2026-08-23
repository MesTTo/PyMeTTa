"""Purpose: examples/control/letext.metta in Python: `let` matches a pattern.

`let` binds by MATCHING a pattern against a value, not by naming a variable:
`($x (42 (if (== $x 2) 43 44)))` meets `(3 (42 $z))`, so `$x` takes 3 from the
left of the value and `$z` takes the still-unrun `(if (== 3 2) 43 44)` from the
right of the pattern. Variables on BOTH sides bind at once, and the body then
evaluates what `$z` holds, so `(+ 3 44)` is 47.

Python's assignment binds one way, into names, so nothing here is an
assignment. A compiled body refuses a tuple target outright, "a compiled body
binds plain names; destructuring and attribute assignment have no let* form",
and even a destructuring assignment would only carry the left-to-right half.
Filed as residue against P14.4.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let` whose pattern and value both carry variables has no assignment spelling"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Bind in both directions at once, then use what was bound."""
    # The top rung is an assignment, which is what a `let` is:
    #     x, (_, z) = 3, (42, ...)
    # It carries only the left-to-right half. Here BOTH sides hold variables
    # and they bind at once, which no Python statement says, and a compiled
    # body refuses a tuple target outright. Residue: P14.4.
    # !(test (let ($x (42 (if (== $x 2) 43 44))) (3 (42 $z)) (+ $x $z)) 47)
    assert m.eval(
        S.let(
            (V.x, (42, S["if"](V.x.eq(2), 43, 44))),
            (3, (42, V.z)),
            V.x + V.z,
        )
    ) == [47]
