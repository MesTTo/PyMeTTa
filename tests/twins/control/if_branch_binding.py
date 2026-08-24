"""Purpose: examples/control/if_branch_binding.metta in Python: arms bind alone.

A conditional arm whose value collapses to a clause parameter must not capture
the clause's output at translate time; the other arm still runs its own
unification. The original found this by differential fuzzing of compiled
programs, and every equation in it is exactly what a Python `if` statement
with an assignment in one arm compiles to:

    if a < a:          -->  (if (< $a $a)
        _c = a         -->      (let* (($c $a)) $a)
        return a
    return b           -->      $b)

so three of the four are written that way and read the same in both languages.
The binding is named `_c` rather than `c` because Python calls a bound name
nothing reads a dead store, and it is not one here: it is the `let*` pair the
defect lives in. `case-else` is the same shape through `case`, which is
Python's `match` statement, and it compiles to the case tower with both arms'
bindings intact.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Take each arm of four conditionals whose arms bind."""
    @m.define
    def pick_else(a, b):
        # (= (pick-else $a $b) (if (< $a $a) (let* (($c $a)) $a) $b))
        if a < a:  # noqa: PLR0124 -- comparing the parameter with itself is the fixture: the then arm must never run, and the else arm must still unify its own output
            _c = a
            return a
        return b

    # !(test (pick-else 1 2) 2)
    assert pick_else(1, 2) == [2]

    @m.define
    def pick_then(a, b):
        # (= (pick-then $a $b) (if (> $a 0) (let* (($c $a)) $a) $b))
        if a > 0:
            _c = a
            return a
        return b

    # !(test (pick-then 1 2) 1)
    assert pick_then(1, 2) == [1]

    @m.define
    def case_else(a, b):
        # (= (case-else $a $b) (case (< $a $a) ((True (let* (($c $a)) $a)) (False $b))))
        match a < a:  # noqa: PLR0124 -- the same fixture, asked through `case` rather than through `if`
            case True:
                _c = a
                return a
            case False:
                return b

    # !(test (case-else 3 4) 4)
    assert case_else(3, 4) == [4]

    @m.define
    def both(a, b):
        # (= (both $a $b) (if (> $a $b) (let* (($c 1)) $a) (let* (($d 1)) $b)))
        if a > b:
            _c = 1
            return a
        _d = 1
        return b

    # !(test (both 5 2) 5)
    assert both(5, 2) == [5]
    # !(test (both 2 5) 5)
    assert both(2, 5) == [5]
