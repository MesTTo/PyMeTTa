"""examples/ch10-errors-and-refusals/02-throwing_and_tracing.metta in Python: an error a program makes for itself.

`throw` does not unwind: it PRODUCES the value `(Error (throw R) R)`, so every
claim here compares an atom rather than catching anything, and the Python
spelling is the value the engine answers.

`trace!` prints its first argument and answers its second, so its claims are
about what flows through it. Both of its arguments are held, which is why the
label is built with `S` and never evaluated on the way in.

`half` takes no annotation and builds both of its operators by word,
`fn.truediv` and `fn.mod`. An annotation would publish a type declaration the
original does not have, and `n / 2` without one would store
`(py-operator truediv ...)` and answer 5.0 where the original stores `(/ ...)`
and answers 5.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, fn


def twin(m):
    """Produce an error, read it, carry it out of a function, and trace."""
    throw, trace = m.fn.throw, m.fn["trace!"]

    ball = S.my_ball(1)
    assert throw(ball) == [S.Error(S.throw(ball), ball)]
    assert throw(G("text")) == [S.Error(S.throw(G("text")), G("text"))]

    # Every form that reads an error reads this one, with no special case for
    # a raised one against a computed one. `return-on-error` answers the
    # error inside minimal MeTTa's own `return` marker.
    assert m.fn.if_error(throw(S.oops)[0], S.caught, S.fine) == [S.caught]
    assert m.fn.if_error(42, S.caught, S.fine) == [S.fine]
    thrown = S.Error(S.throw(S.oops), S.oops)
    assert m.fn["return-on-error"](thrown, S.carried_on) == [S["return"](thrown)]
    assert m.fn["return-on-error"](42, S.carried_on) == [S.carried_on]

    # A reason that is ALREADY an error passes through unchanged rather than
    # being wrapped twice, so rethrowing does not bury the original cause.
    inner = S.Error(S.inner(1), S.because)
    assert throw(inner) == [inner]
    assert throw(throw(S.first)[0]) == [S.Error(S.throw(S.first), S.first)]

    # It travels out of a function the way any answer does, so a guard clause
    # is an ordinary equation.
    @m.define
    def half(n):
        # (= (half $n) (if (== (% $n 2) 0) (/ $n 2) (throw (odd $n))))
        return fn.truediv(n, 2) if fn.eq(fn.mod(n, 2), 0) else fn.throw(S.odd(n))

    assert m.fn.half(10) == [5]
    odd = S.Error(S.throw(S.odd(7)), S.odd(7))
    assert m.fn.half(7) == [odd]
    assert m.fn.if_error(odd, S.refused, 0) == [S.refused]

    # `trace!` prints its first argument and answers its SECOND, so it drops
    # into the middle of an expression without changing what flows through.
    assert trace(G("the answer"), 42) == [42]
    traced = S["trace!"](G("adding one to"), 41)  # rung: trace! answers its SUBJECT, which print() cannot
    assert m.answers(1 + traced) == [42]
    assert trace(m.fn.half(10)[0], m.fn.half(10)[0]) == [5]

    # Both arguments are held, so the label can be any atom and is written as
    # the program spelled it.
    assert trace(S.checking(S.odd(7)), S.ok) == [S.ok]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 16351 inferences, 1.1505x the example's 14212; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 16351
