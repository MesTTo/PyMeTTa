"""Purpose: examples/control/if4.metta in Python: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does, and this file's whole subject is that nesting. All three `if`s
are Python conditional expressions and the file compiles whole.

Two lowerings the equation makes visible. Python's `==` is the prelude's
`py-eq`, which is Python's equality rather than MeTTa's `==`; and a test
position that is not already boolean by its syntax wraps in `py-truthy`, so an
`if` used as a condition is asked for its truth the way Python asks. The stored
equation is
`(if (py-truthy (if (py-eq 42 42) True False)) (if True 42 lol) (+ 2 2))`.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Decide a condition with an `if`, then take an arm with another."""
    @m.define
    def nested():
        # (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2))
        return (42 if True else S.lol) if (True if 42 == 42 else False) else 2 + 2  # noqa: PLR0133  -- comparing two constants is the example's own program, which the engine reduces

    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    assert nested() == [42]
