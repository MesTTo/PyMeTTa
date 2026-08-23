"""examples/basics/relational_arithmetic.metta in Python: CLP(FD) both ways.

The `#` operators are constraints rather than evaluations, so they run in
every direction: give any two of the three and the engine solves for the
third, by propagation rather than by search.

Two doors, one per job, and this file uses both deliberately. `m.fn["#+"]`
CALLS the constraint, so `plus(1, 2)` answers `[3]` and reads as Python;
`fn["#+"]` is the static namespace, whose members are the symbols themselves,
so it BUILDS the term, which is what a backward query needs, because the
thing being solved for has to reach the engine unevaluated. Python has no `#+`
and should not: these are MeTTa names, and the subscript is the door for a
name Python's own grammar will not take.

Running one backwards is `m.solve(pattern, subject)`: the known value on
`let`'s pattern side, the constraint on its subject side, and the answer
projected by the variable's own name.
"""

from petta import V, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Run each constraint forwards, then run three of them backwards."""
    # COST, recorded because the lane's band reports it and it is the
    # library's to fix, not this twin's: `m.fn[...]` resolves its handle
    # against the engine on every access, about 1,200 inferences per name,
    # and this file names fourteen. With the first answer view's own ~4,700
    # setup that is most of the twin's 24,730 against the example's 19,446.
    # Nothing about the spelling changes; the resolution should be cached
    # [measured 2026-08-23: 1,206 for the first name and 1,178 for the second,
    # with m.stats() around one m.fn["#<"] and one m.fn["#>"] access;
    # commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    plus, times, minus = m.fn["#+"], m.fn["#*"], m.fn["#-"]
    divide, modulo = m.fn["#div"], m.fn["#mod"]
    smallest, largest = m.fn["#min"], m.fn["#max"]
    less, greater = m.fn["#<"], m.fn["#>"]
    equal, unequal = m.fn["#="], m.fn[r"#\="]
    at_most, at_least = m.fn["#=<"], m.fn["#>="]

    # Forwards, the same as ordinary arithmetic.
    assert plus(1, 2) == [3]
    assert times(3, 4) == [12]
    assert minus(10, 4) == [6]

    # Backwards: the result is known and the operand is not.
    assert m.solve(5, fn["#+"](V.x, 2)).x == 3
    assert m.solve(12, fn["#*"](V.y, 4)).y == 3
    assert m.solve(6, fn["#-"](V.z, 4)).z == 10

    # Integer division, remainder, and the two extremes.
    assert divide(13, 4) == [3]
    assert modulo(13, 4) == [1]
    assert smallest(3, 7) == [3]
    assert largest(3, 7) == [7]

    # All six comparisons answer True or False rather than succeeding or
    # failing, so they compose with `if`.
    assert less(1, 2) == [True]
    assert less(2, 1) == [False]
    assert greater(2, 1) == [True]
    assert equal(3, 3) == [True]
    assert unequal(3, 4) == [True]
    assert at_most(1, 2) == [True]
    assert at_most(2, 1) == [False]
    assert at_least(2, 1) == [True]
    assert at_least(1, 2) == [False]

    # Composed, and still solvable backwards through two constraints.
    assert m.solve(20, fn["#*"](fn["#+"](V.a, 1), 4)).a == 4
