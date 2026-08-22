"""Purpose: examples/basics/time_and_pragmas.metta in Python: bounds, time and pragmas.

Three of the four bounding forms have a Python door and take it. `timeout` and
`inferences` are per-call keywords, so `(timeout 30 (spin 100))` is
`m.eval(spin(100), timeout=30)`; `with-pragma!` scopes settings to a region,
so it is `with m.limits(...)`, which is the same shape and the same undo. The
fourth, `pragma!`, sets a process-wide interpreter setting and has no Python
door at all, so it is built as the atom it is. `car-atom` dissolves as well:
`elapsed` answers `(Value Seconds)` and Python reads the value as `[0]`.

Two rungs are dropped here and both are named on the line. `metta/3` takes the
space by NAME, and handing it the space handle fails inside the engine's own
writer, so `&self` is written as the symbol it wants; the same wall is why
`evalc`, which does have a handle door, is spelled `m.space("&self").eval`
right beside it, and the two doors sitting next to each other is the point of
those two forms. And `spin`'s equation answers the lowercase symbol `done`,
which a compiled body cannot name, so it is written at the container door.

`bounded-factorial` needs the definitional door that derives NO first-match
guard: its two clauses are non-exclusive and both apply at 0, which is what
makes the runaway branch reachable at all. `@m.define` would emit
`(if (== $n 0) (empty) ...)` and prune it, so `@rules` is the door.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import UNIT, S, V, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 43549 to 33675, -9874 (-22.7%), by the twin
#: contract change: twenty-four `test` wrappers left the engine for
#: `assert`, two `collapse` calls and one `car-atom` left it for the answer
#: list and `[0]`, and four bounding forms left it for keywords and a
#: with-block: `timeout`, `inferences` and both `with-pragma!` scopes are
#: now `m.eval(..., timeout=)`, `inferences=` and `with m.limits(...)`. The
#: seven `pragma!` forms and the runaway factorial stayed. Against the
#: example's 64046 the ratio is 0.5258 [measured 2026-08-22 min-of-3,
#: `twin_coverage.py --measure`]. The old figure priced a different
#: program.
BUDGET = 33675


def twin(m):
    """Bound four evaluations, set seven pragmas, then invert arithmetic."""

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

    # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done)). The body answers the
    # lowercase symbol `done`, which a compiled body cannot name: a free
    # lowercase name there is a call it cannot resolve.
    spin = S.spin
    body = S["if"](V.n > 0, spin(V.n - 1), S.done)  # rung: `done` unnameable in a body
    m += equation(spin(V.n)).to(body)

    # A bound that is not reached is invisible.
    assert m.eval(spin(100), timeout=30) == [S.done]
    assert m.eval(S["+"](1, 2), timeout=30) == [3]

    # Bounding an expression does NOT collapse it to one answer: the whole
    # answer set computes under the bound.
    assert m.eval(S.superpose((1, 2, 3)), timeout=30) == [1, 2, 3]

    # elapsed answers (Value Seconds), so timing a call does not mean writing
    # the clock by hand. Only the value is asserted; the duration is real but
    # not reproducible enough to assert on.
    assert m.one(S.elapsed(spin(100)))[0] == S.done

    # sleep answers True, so it sequences with anything else.
    assert m.fn("sleep")(0.01) is True

    # metta/3 interprets an atom in a NAMED space; PeTTa's evalc already is
    # that, since PeTTa's eval is full evaluation rather than one rewriting
    # step, so the two agree.
    interpreted = S.metta(S["+"](1, 2), S["%Undefined%"], S["&self"])  # rung: space by name
    assert m.eval(interpreted) == [3]
    assert m.space("&self").eval(S["+"](1, 2)) == [3]

    # Pragmas. Each answers the unit value, the way add-atom and print do.
    # Every key must be in the interpreter registry, and a bound's value is
    # checked before it replaces a working setting.
    pragma = S["pragma!"]
    assert m.eval(pragma(S["max-time"], 30)) == [UNIT]
    assert m.eval(pragma(S["max-inferences"], 100000000)) == [UNIT]
    # Passing none clears a bound again.
    assert m.eval(pragma(S["max-time"], S.none)) == [UNIT]
    assert m.eval(pragma(S["max-inferences"], S.none)) == [UNIT]

    # max-stack-depth answers its own error rather than raising: the count it
    # requires is checked in the answer, so the program that wrote it runs on.
    assert m.eval(pragma(S["max-stack-depth"], 0)) == [UNIT]
    assert m.eval(pragma(S["max-stack-depth"], -1)) == [
        S.Error(pragma(S["max-stack-depth"], -1), S.UnsignedIntegerIsExpected)
    ]
    assert m.eval(pragma(S["max-stack-depth"], S.none)) == [UNIT]

    # A positive stack-depth setting caps the evaluator's branch-local fuel,
    # and a finite sibling survives when an overlapping recursive branch runs
    # out.
    m.eval(pragma(S["max-stack-depth"], 20))

    @rules
    def bounded_factorial(n):
        # (= (bounded-factorial 0) 1)
        yield equation(S["bounded-factorial"](0)).to(1)
        # (= (bounded-factorial $n) (* $n (bounded-factorial (- $n 1))))
        yield equation(S["bounded-factorial"](n)).to(n * S["bounded-factorial"](n - 1))

    m.add(*bounded_factorial)
    assert m.eval(S["bounded-factorial"](5)) == [120, S.Error(-3, S.StackOverflow)]

    m.eval(pragma(S["max-stack-depth"], S.none))

    # (inferences $n $expr) is timeout's deterministic twin: the bound stops
    # at the same step on every machine, and it is the same keyword.
    assert m.eval(spin(100), inferences=100000) == [S.done]
    assert m.eval(S.superpose((1, 2, 3)), inferences=100000) == [1, 2, 3]

    # with-pragma! scopes settings to ONE expression; a with-block scopes them
    # to a region, and the previous values come back on every exit path.
    with m.limits(inferences=100000):
        assert m.eval(S["+"](20, 22)) == [42]
    with m.limits(timeout=30, inferences=100000):
        assert m.eval(spin(100)) == [S.done]
    assert m.eval(spin(2000)) == [S.done]

    # Relational integer arithmetic: one unbound argument among integers
    # solves for it. Exactness is honest, so a branch with no integer answer
    # answers nothing rather than something approximate.
    assert m.one(solve(4, V.x - 1, V.x)) == 5
    assert m.one(solve(10, V.x + 3, V.x)) == 7
    assert m.one(solve(6, V.x * 2, V.x)) == 3
    assert m.one(solve(3, V.x / 2, V.x)) == 6
    assert m.eval(solve(7, V.x * 2, V.x)) == []
