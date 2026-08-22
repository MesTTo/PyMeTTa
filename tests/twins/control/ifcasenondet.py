"""The Python twin of examples/control/ifcasenondet.metta: a nondeterministic test.

`if` and `case` both take their condition from an ordinary expression, so a
condition that answers three times makes the whole form answer three times.
Nondeterminism is not a special case here; it is what an argument position
already is.

Both equations are written at the container door and two holes explain it.
`(superpose $y)` superposes a BOUND value, and `superpose(y)` in a compiled
body means `(superpose ($y))`, one alternative that happens to be `$y`; a
generator's `yield from y` does spell `(superpose $y)`, but only in yield
position and this one sits in a condition. And `a` and `b` are lowercase
SYMBOLS: a compiled body resolves a lowercase free name as a function and
reads a capitalised one as a constructor, which wave one recorded against
P14.4 for `time_and_pragmas`.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3490 to 3789, +299, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 3490 by 47554fc's control/types twin baseline.
BUDGET = 3789


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (if-nondet $y) (if (superpose $y) a b))
    m += S["="](
        S["if-nondet"](V.y),
        S["if"](S["superpose"](V.y), S.a, S.b),
    )

    # (= (case-nondet $y)
    #    (case (superpose $y)
    #          ((True a)
    #           (False b))))
    m += S["="](
        S["case-nondet"](V.y),
        S["case"](
            S["superpose"](V.y),
            expr(expr(TRUE, S.a), expr(FALSE, S.b)),
        ),
    )

    # !(test (collapse (if-nondet (True False True))) (a b a))
    yield m.eval(
        S.test(
            S["collapse"](S["if-nondet"](expr(TRUE, FALSE, TRUE))),
            expr(S.a, S.b, S.a),
        )
    )

    # !(test (collapse (case-nondet (True False True))) (a b a))
    yield m.eval(
        S.test(
            S["collapse"](S["case-nondet"](expr(TRUE, FALSE, TRUE))),
            expr(S.a, S.b, S.a),
        )
    )
