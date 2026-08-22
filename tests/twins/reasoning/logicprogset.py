"""The Python twin of examples/reasoning/logicprogset.metta: a set from a check.

`myf` is written at the container door because MeTTa's `and` is not Python's.
Python's `and` short-circuits on truthiness and lowers to a `let*`-then-`if`
chain, while `(and (member a $M) (member b $M))` is a generate-and-test that
lets the first conjunct BIND `$M` for the second. That binding is the whole
example, so the equation is built as the term it is, with `&` for `and` and
`.eq` for `==`, which are the two operators the term door already spells:
`x & y` is `(and x y)` and Python's `==` is structural equality, so the
equality TERM is `x.eq(y)`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 2948 across the term-door rewrite: `equation(...).to(...)`,
#: `&` and `.eq` build the same atom the hand-nested `expr` calls built, which
#: the atom-level differential confirms byte-for-byte. Prior: ADDED 2026-08-22
#: at 2948 by the wave-3 twin baseline.
BUDGET = 2948


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (myf $M)
    #    (and (and (member a $M)
    #              (member b $M))
    #         (== (size-atom $M) 2)))
    m += equation(S.myf(V.M)).to(
        S.member(S.a, V.M) & S.member(S.b, V.M) & S["size-atom"](V.M).eq(2)
    )

    # !(test (if (once (myf $M)) $M)
    #        (a b))
    yield m.eval(S.test(S["if"](S.once(S.myf(V.M)), V.M), (S.a, S.b)))
