"""The Python twin of examples/spaces/spaces2.metta: what is stored and what is only run.

Four facts are stored, two `!(bar ...)` forms are only EVALUATED, and the closing
assertion collects everything the space actually holds. `(bar 42)` matches nothing
because evaluating a form never stores it, which is the whole distinction the
example draws.

The facts are plain tuples, which is the knowledge front's own shape: MeTTa's
`(foo 42 42)` reads as `(S.foo, 42, 42)` and nests, so `(foo (42 42))` is
`(S.foo, (42, 42))`.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3575 to 5204, +1629 (+45.6%), by the P14 twin-style
#: rewrite, and the whole delta is one cause: `(= (answer) 42)` moved from the
#: container door to @m.define. 1,629 is the decorator door's price for the
#: FIRST decorated function in a process, measured in isolation as 2,244
#: against the container door's 615; a second equation costs 193 more rather
#: than 1,629, so the bulk of it is one-time machinery. The four tuple facts
#: and the two evaluated forms measure exactly as their expr() spellings did.
#: Prior: ADDED 2026-08-22 at 3575 by the wave-3 spaces baseline.
BUDGET = 5204


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    here = S[m.space_name]

    # (foo 1) (foo 2) (foo 42 42) (foo (42 42))
    m += (S.foo, 1)
    m += (S.foo, 2)
    m += (S.foo, 42, 42)
    m += (S.foo, (42, 42))

    # Evaluated, not stored: nothing defines bar, so each answers itself.
    # !(bar 42)
    yield m.eval(S.bar(42))
    # !(bar 43)
    yield m.eval(S.bar(43))

    # (= (answer) 42)
    @m.define
    def answer():
        return 42

    # !(test (space (msort (collapse (superpose ((match &self (foo $1) (foo $1))
    #                                            (match &self (foo $1 $2) (foo $1 $2))
    #                                            (match &self (bar $1) (bar $1)))))) (answer))
    #        (space ((foo 1) (foo 2) (foo 42 42) (foo (42 42))) 42))
    yield m.eval(
        S.test(
            S.space(
                S.msort(
                    S.collapse(
                        S.superpose(
                            (
                                S.match(here, S.foo(V.x), S.foo(V.x)),
                                S.match(here, S.foo(V.x, V.y), S.foo(V.x, V.y)),
                                S.match(here, S.bar(V.x), S.bar(V.x)),
                            )
                        )
                    )
                ),
                S.answer(),
            ),
            S.space(
                (S.foo(1), S.foo(2), S.foo(42, 42), S.foo((42, 42))),
                42,
            ),
        )
    )
