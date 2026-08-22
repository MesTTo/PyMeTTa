"""examples/basics/relational_arithmetic.metta in Python: CLP(FD) both ways.

The `#` operators are constraints rather than evaluations, so they run in
every direction: give any two of the three and the engine solves for the
third, by propagation rather than by search.

Two doors, one per job, and this file uses both deliberately. `m.fn("#+")`
CALLS the constraint, so `plus(1, 2)` is 3 and reads as Python; `S["#+"]`
BUILDS the term, which is what a backward query needs, because the thing
being solved for has to reach the engine unevaluated. Python has no `#+` and
should not: these are MeTTa names, and the subscript is the door for a name
Python's own grammar will not take.

Running one backwards is the file's one dropped rung, named once as `solve`,
the same way examples/basics/backward_arithmetic.metta's twin names it.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11839 to 4728, -7111 (-60.1%), by the twin
#: contract change: twenty `test` wrappers left the engine for `assert`,
#: and sixteen forward constraints are now ordinary Python calls through
#: `m.fn`; the four backward ones still build their `let` term and run in
#: the engine. Against the example's 19437 the ratio is 0.2432 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 4728


def twin(m):
    """Run each constraint forwards, then run three of them backwards."""

    def solve(pattern, subject, answer):
        """Unify `pattern` with what `subject` produces, then answer `answer`.

        Either side may be the call, which is what makes it run BACKWARDS: the
        call's own variables come out bound. This is MeTTa's `let`, which
        dissolves into Python's assignment when the subject is a call and the
        pattern is a fresh name; the direction used here, a pattern the call
        has to reach, has no Python spelling at all. The design's name for the
        door it wants is `solve` (ai-python-first-revamp-discussion.md section
        9g, idea 1), and the residue table records it against P14.4.
        """
        return S.let(pattern, subject, answer)  # rung: relational let

    plus, times, minus = m.fn("#+"), m.fn("#*"), m.fn("#-")
    divide, modulo = m.fn("#div"), m.fn("#mod")
    smallest, largest = m.fn("#min"), m.fn("#max")
    less, greater = m.fn("#<"), m.fn("#>")
    equal, unequal = m.fn("#="), m.fn(r"#\=")
    at_most, at_least = m.fn("#=<"), m.fn("#>=")

    # Forwards, the same as ordinary arithmetic.
    assert plus(1, 2) == 3
    assert times(3, 4) == 12
    assert minus(10, 4) == 6

    # Backwards: the result is known and the operand is not.
    assert m.one(solve(5, S["#+"](V.x, 2), V.x)) == 3
    assert m.one(solve(12, S["#*"](V.y, 4), V.y)) == 3
    assert m.one(solve(6, S["#-"](V.z, 4), V.z)) == 10

    # Integer division, remainder, and the two extremes.
    assert divide(13, 4) == 3
    assert modulo(13, 4) == 1
    assert smallest(3, 7) == 3
    assert largest(3, 7) == 7

    # All six comparisons answer True or False rather than succeeding or
    # failing, so they compose with `if`.
    assert less(1, 2) is True
    assert less(2, 1) is False
    assert greater(2, 1) is True
    assert equal(3, 3) is True
    assert unequal(3, 4) is True
    assert at_most(1, 2) is True
    assert at_most(2, 1) is False
    assert at_least(2, 1) is True
    assert at_least(1, 2) is False

    # Composed, and still solvable backwards through two constraints.
    assert m.one(solve(20, S["#*"](S["#+"](V.a, 1), 4), V.a)) == 4
