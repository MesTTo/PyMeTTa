"""examples/control/if4.metta in Python: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does, and this file's whole subject is that nesting. All three `if`s
are Python conditional expressions and the file compiles whole.

Two lowerings the equation makes visible. Python's `==` is the prelude's
`py-eq`, which is Python's equality rather than MeTTa's `==`; and a test
position that is not already boolean by its syntax wraps in `py-truthy`, so an
`if` used as a condition is asked for its truth the way Python asks. The stored
equation is
`(if (py-truthy (if (py-eq 42 42) True False)) (if True 42 Lol) (+ 2 2))`.
"""

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1004 to 4255, +3251 (+323.8%), by lifting this twin
#: to the definitional door now that the band pays for authoring: all three
#: `if`s ENTERED the engine as compiled Python conditional expressions, so
#: the whole form is now one equation and nothing about it is stated as a
#: term. Measured min-of-3 over fresh processes with the MORK backend linked
#: in; against the example's 2667 the ratio is 1.5954, and the ceiling is
#: 5155, the example plus 10% plus 2221 to author 1 definition. Prior: 1004,
#: the term-door twin the old band forced.
BUDGET = 4255


def twin(m):
    """Decide a condition with an `if`, then take an arm with another."""
    @m.define
    def nested():
        # (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2))
        return (42 if True else Lol) if (True if 42 == 42 else False) else 2 + 2  # noqa: F821, PLR0133  -- `Lol` is a capitalised free name, which a compiled body reads as MeTTa data with no Python value to bind; and comparing two constants is the example's own program, which the engine reduces

    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    assert nested() == [42]
