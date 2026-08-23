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
defect lives in. `case-else` is the same shape through `case`, which Python's
`match` statement would spell and the compiled subset has no lowering for yet
(P14.4); writing it as an `if` would only repeat the equation above it, so it
stays a term.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S, V, equation

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
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

    # The top rung is the same `if` statement above, written through
    # Python's `match`, which is what a MeTTa `case` is:
    #
    #     @m.define(name="case-else")
    #     def case_else(a, b):
    #         match a < a:
    #             case True:
    #                 _c = a
    #                 return a
    #             case False:
    #                 return b
    #
    # `ast.Match` has no lowering in the compiled subset. Residue: P14.4.
    # (= (case-else $a $b) (case (< $a $a) ((True (let* (($c $a)) $a)) (False $b))))
    arms = ((TRUE, S["let*"](((V.c, V.a),), V.a)), (FALSE, V.b))  # rung: a `case` is Python's `match` statement, which has no lowering yet
    m += equation(S["case-else"](V.a, V.b)).to(S.case(S["<"](V.a, V.a), arms))  # rung: the same

    # !(test (case-else 3 4) 4)
    assert m.eval(S["case-else"](3, 4)) == [4]

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
