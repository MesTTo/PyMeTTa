"""examples/basics/backward_arithmetic.metta in Python: arithmetic run backwards.

`+ - * /` are RELATIONS: give any two of the three and the engine solves for
the third, so a function written forwards reads backwards for free. Past one
unknown the rearrangement runs out and a CONSTRAINT begins, which is what the
`#` family is for, and past that the engine refuses by name rather than
guessing.

Both definitions are ordinary Python functions, and every backward query is
built with Python's own operators, because an operator over an atom BUILDS
the term (`V.p + 2` is `(+ $p 2)`) and a backward query always has a variable
in it. What has no Python spelling is the inversion itself, and `solve` below
is the one place this file drops a rung: it names the door the design wants
so the twelve call sites read as Python rather than as `let`.

An expected answer is a Python tuple, which encodes to the expression the
original writes, and a collapse is the list an evaluation already answers, so
the original's `(noeval ...)` wrappers have nothing to guard against here: a
Python list is data and is never evaluated a second time.
"""

from petta import S, V, val

#: MeTTa's boolean ATOM, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and this is an answer.
TRUE = val(value=True)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 40680 to 32289, -8391 (-20.6%), by the twin
#: contract change: the `test` wrapper and eleven `collapse` calls left the
#: engine for `assert` and the list an evaluation already answers, while
#: every backward query and both definitions stayed exactly where they
#: were. Against the example's 53467 the ratio is 0.6039 [measured
#: 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old figure
#: priced a different program.
BUDGET = 32289


def twin(m):
    """Run two functions forwards, then run everything backwards."""

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

    @m.define
    def double(x):
        # (= (double $x) (* 2 $x))
        return 2 * x

    assert double(5) == [10]
    assert m.one(solve(10, S.double(V.x), V.x)) == 5

    # Each operator solves for its one unbound slot.
    assert m.one(solve(5, V.p + 2, V.p)) == 3
    assert m.one(solve(12, V.q * 4, V.q)) == 3
    assert m.one(solve(6, V.r - 4, V.r)) == 10
    assert m.one(solve(3, V.s / 4, V.s)) == 12

    # No integer doubles to 7, so the query FAILS rather than erroring: no
    # answers at all, which is what collapsing it to `()` says.
    assert m.eval(solve(7, S.double(V.x), V.x)) == []

    @m.define
    def square(x):
        # (= (square $x) (* $x $x))
        return x * x

    # Past one unknown a constraint begins: 25 = X*X is nonlinear, so the
    # engine posts it to CLP(FD) and labels what propagation leaves, which
    # answers EVERY solution rather than one.
    assert m.eval(solve(25, S.square(V.x), V.x)) == [-5, 5]
    assert [tuple(pair) for pair in m.eval(solve(25, V.x * V.y, (V.x, V.y)))] == [
        (-25, -1), (-5, -5), (-1, -25), (1, 25), (5, 5), (25, 1),
    ]

    # A domain the constraint leaves unbounded has nothing finite to search,
    # so the engine refuses by name. Bounding the unknown first is what the
    # refusal asks for, and the `#` family is how a MeTTa program bounds one.
    bounded = solve(TRUE, S["#>="](V.x, 0), solve(25, S.square(V.x), V.x))
    assert m.eval(bounded) == [5]

    # THE LIMIT: ordinary evaluation is inside-out, so a composed backward
    # query reaches the INNER operation with two unknowns and refuses. The `#`
    # operators POST rather than solve, so the inner constraint waits for the
    # outer one to narrow it and the same query answers.
    composed = solve(20, S["#*"](S["#+"](V.a, 1), 4), V.a)
    assert m.one(composed) == 4

    divide, modulo = m.fn("#div"), m.fn("#mod")
    smallest, largest = m.fn("#min"), m.fn("#max")
    less, greater = m.fn("#<"), m.fn("#>")
    equal, unequal = m.fn("#="), m.fn(r"#\=")
    at_most, at_least = m.fn("#=<"), m.fn("#>=")

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
    assert m.one(composed) == 4
