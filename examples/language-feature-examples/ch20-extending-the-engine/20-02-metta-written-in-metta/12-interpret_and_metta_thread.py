"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/12-interpret_and_metta_thread.metta in Python: three evaluator doors, two answers.

All three take the atom, a type and the space to run it in, and the atom
arrives HELD, so every subject here is built with `S` and never called from
Python. The space is a handle, which is what `m` and the second space are.

They part on a body whose answer is itself reducible: `interpret` and `metta`
hand back the carrier they stepped, and `metta-thread` runs to a fixpoint.
The held-call answers are read through `str`, because `m.fn.repr` EVALUATES
its operand -- it would print 3 where the point is that the answer is still
`(+ 1 2)` -- and because Python's own `1 + 2` is 3 rather than a term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, arrow, fn

UNDEFINED = S["%Undefined%"]


def twin(m):
    """One step against a fixpoint, over the same three arguments."""
    interpret = m.fn.interpret
    metta_ = m.fn.metta
    threaded = m.fn["metta-thread"]

    @m.define
    def twice(x: int) -> int:
        # (= (twice $x) (* 2 $x))
        return 2 * x

    # On an ordinary call all three agree, because one step is all it takes.
    assert metta_(S.twice(5), UNDEFINED, m) == [10]
    assert interpret(S.twice(5), UNDEFINED, m) == [10]
    assert threaded(S.twice(5), UNDEFINED, m) == [10]
    assert interpret(fn.add(1, 2), S.Number, m) == [3]

    # They agree on nondeterminism too: each answers once per branch rather
    # than collapsing.
    @m.define
    def gen():
        # (= (gen) (superpose (1 2)))
        return fn.superpose((1, 2))

    assert interpret(S.gen(), UNDEFINED, m) == [1, 2]
    assert threaded(S.gen(), UNDEFINED, m) == [1, 2]

    # They part on a body whose ANSWER is itself reducible.
    @m.define
    def held():
        # (= (held) (noeval (+ 1 2)))
        return fn.noeval(1 + 2)

    assert str(interpret(S.held(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert str(metta_(S.held(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert threaded(S.held(), UNDEFINED, m) == [3]

    # A function frame is the same story: `return` hands one value back to
    # the frame and the two step-at-a-time doors stop there.
    @m.define
    def framed():
        # (= (framed) (function (return (+ 1 2))))
        return fn.function(S["return"](1 + 2))

    assert str(interpret(S.framed(), UNDEFINED, m)[0]) == "(+ 1 2)"
    assert threaded(S.framed(), UNDEFINED, m) == [3]

    # An atom nothing reduces is its own answer through every one of them.
    assert interpret(S.nosuchhead, UNDEFINED, m) == [S.nosuchhead]
    assert threaded(S.nosuchhead, UNDEFINED, m) == [S.nosuchhead]

    # Two are declared and the third is not, which is why the first two mask
    # their atom argument and the third is a bare operation.
    stepper = arrow(S.Atom, S.Type, S.SpaceType, S.Atom)
    assert m.type(S.interpret) == stepper
    assert m.type(S.metta) == stepper
    assert m.type(S.metta_thread) == UNDEFINED

    # The space argument is the point of all three: an atom evaluates against
    # the equations of the space it is handed, not of the caller's.
    elsewhere = m.metta.space(S.elsewhere)
    elsewhere += S["="](S.twice(V_X), 1000 + V_X)
    assert interpret(S.twice(5), UNDEFINED, elsewhere) == [1005]
    assert threaded(S.twice(5), UNDEFINED, elsewhere) == [1005]
    assert interpret(S.twice(5), UNDEFINED, m) == [10]


from metta import V  # noqa: E402  -- the one variable the elsewhere equation binds

V_X = V.x

#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 30158 inferences, 1.0577x the example's 28514; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 30158
