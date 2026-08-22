"""The Python twin of examples/libraries/test_memo_stats.metta.

One miss and two hits on the same key, all answering 81.

`@m.define` writes the equation; the definition is installed ahead of the
runnable forms for the loader-ordering reason the residue table records against
P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 127317 to 128946, +1629 (+1.28%), by the P14
#: twin-style rewrite: the equation is now written by @m.define, which
#: COMPILES the body from Python syntax where the container door added an
#: already-built atom. The compile costs 1,629 inferences, once per decorated
#: function: test_memo_stats holds one define too and moved by the same
#: amount. Prior: ADDED 2026-08-22 at 127317 by the wave-3 libraries
#: baseline, which recorded no cause.
BUDGET = 128946


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define
    def sq(x):
        # (= (sq $x) (* $x $x))
        return x * x

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(memoize sq)
    yield m.eval(S.memoize(S.sq))

    # One miss, then two hits on the same key (9*9 = 81).
    # !(test (sq 9) 81)
    yield m.eval(S.test(S.sq(9), 81))
    # !(test (sq 9) 81)
    yield m.eval(S.test(S.sq(9), 81))
    # !(test (sq 9) 81)
    yield m.eval(S.test(S.sq(9), 81))
