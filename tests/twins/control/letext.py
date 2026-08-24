"""Purpose: examples/control/letext.metta in Python: `let` matches a pattern.

`let` binds by MATCHING a pattern against a value, not by naming a variable:
`($x (42 (if (== $x 2) 43 44)))` meets `(3 (42 $z))`, so `$x` takes 3 from the
left of the value and `$z` takes what the right of the pattern holds.
Variables on BOTH sides bind at once, and the body then adds them, so the
answer is 47.

That is exactly the cell `solve` fills: assignment is the `let` whose pattern
is a fresh name, and `solve(pattern, subject)` is the `let` whose PATTERN must
win variables. Its answer carries BOTH sides' variables, `.x` from the pattern
and `.z` from the subject, already reduced, and the template is then whatever
Python writes with them. The `if` inside the pattern is `if_`, the keyword
builder for stored code, and the equality inside it is built by its operator
WORD, because `==` between two atoms is Python's structural test rather than a
term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, if_, solve

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Bind in both directions at once, then use what was bound."""
    # !(test (let ($x (42 (if (== $x 2) 43 44))) (3 (42 $z)) (+ $x $z)) 47)
    with m:
        bound = solve((V.x, (42, if_(S.eq(V.x, 2), 43, 44))), (3, (42, V.z)))
    assert m.eval(bound.x + bound.z) == [47]
