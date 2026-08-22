"""The Python twin of examples/libraries/test_memo_aggregate.metta.

Aggregating mode folds a ground call's whole answer set into one cached value.

`yield` IS nondeterminism, so the source's three equations for one head are one
`@m.define` generator superposing the three alternatives; a second decorator
under the same head replaces the first rather than stacking beside it, which the
residue table records against P14.4. The definition is installed ahead of the
runnable forms for the loader-ordering reason on the same row.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 130573 to 130374, -199 (-0.15%), by the P14 twin-
#: style rewrite: the three equations for one head become one @m.define
#: generator body, so two clause installs and two clause lookups per call
#: disappear and the compile of the remaining one costs less than they did.
#: Prior: ADDED 2026-08-22 at 130573 by the wave-3 libraries baseline, which
#: recorded no cause.
BUDGET = 130374


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    @m.define
    def choices(x):
        # (= (choices $x) $x)
        # (= (choices $x) (+ $x 1))
        # (= (choices $x) (+ $x 2))
        yield x
        yield x + 1
        yield x + 2

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # Aggregate all answers for ground calls into one cached value.
    # !(config-memoize (aggregate sum))
    yield m.eval(S["config-memoize"](S.aggregate(S.sum)))

    # !(memoize choices)
    yield m.eval(S.memoize(S.choices))

    # sum(5,6,7) => 18
    # !(test (choices 5) 18)
    yield m.eval(S.test(S.choices(5), 18))

    # Restore default mode for follow-up runs in the same session.
    # !(config-memoize (aggregate none))
    yield m.eval(S["config-memoize"](S.aggregate(S.none)))
