"""The Python twin of examples/libraries/test_memo_per_arity.metta.

Memoization is per (name, arity): caching `add` at arity 2 leaves arity 3 alone.

The two-argument equation is written by `@m.define`. The three-argument one is
written at the container door because a SECOND `@m.define` under one MeTTa name
raises IndexError from the twin dispatcher rather than defining another arity;
the residue table records that defect against P14.4. The definitions are
installed ahead of the runnable forms for the loader-ordering reason on the
same row.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 130265 to 131896, +1631 (+1.25%), by the P14
#: twin-style rewrite: the two-argument equation is now compiled from Python
#: syntax by @m.define instead of added as an already-built atom, and the
#: compile costs 1,631 inferences once. Prior: ADDED 2026-08-22 at 130265 by
#: the wave-3 libraries baseline, which recorded no cause.
BUDGET = 131896


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define(name="add")
    def add_two(x, y):
        # (= (add $x $y) (+ $x $y))
        return x + y

    # (= (add $x $y $z) (+ (+ $x $y) $z))
    m += equation(S.add(V.x, V.y, V.z)).to(V.x + V.y + V.z)

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(memoize add 2)
    yield m.eval(S.memoize(S.add, 2))

    # !(test (add 3 4) 7)
    yield m.eval(S.test(S.add(3, 4), 7))
    # !(test (add 3 4) 7)
    yield m.eval(S.test(S.add(3, 4), 7))

    # The uncached arity answers the same way, cache or no cache.
    # !(test (add 1 2 3) 6)
    yield m.eval(S.test(S.add(1, 2, 3), 6))

    # !(test (add 5 6) 11)
    yield m.eval(S.test(S.add(5, 6), 11))
    # !(test (add 5 6) 11)
    yield m.eval(S.test(S.add(5, 6), 11))
