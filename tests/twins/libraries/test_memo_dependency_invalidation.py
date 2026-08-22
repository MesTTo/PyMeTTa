"""The Python twin of examples/libraries/test_memo_dependency_invalidation.metta.

The call that misses the cache and the call that hits it answer the same.

`double` is authored as the Python function it is and `@m.define` writes the
equation, so lib_memo caches the same compiled clause the source produces. The
definition is installed ahead of the runnable forms because the file loader
precompiles equations before running any `!` form, and `!(memoize double)` sits
above the definition in the source; the residue table records that ordering
against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 127000 to 128629, +1629 (+1.28%), by the P14
#: twin-style rewrite: the equation is now written by @m.define, which
#: COMPILES the body from Python syntax where the container door added an
#: already-built atom. The compile costs 1,629 inferences, once per decorated
#: function: test_memo_stats holds one define too and moved by the same
#: amount. Prior: ADDED 2026-08-22 at 127000 by the wave-3 libraries
#: baseline, which recorded no cause.
BUDGET = 128629


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define
    def double(x):
        # (= (double $x) (+ $x $x))
        return x + x

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(memoize double)
    yield m.eval(S.memoize(S.double))

    # First call caches, second uses the cache, and both answer 10.
    # !(test (double 5) 10)
    yield m.eval(S.test(S.double(5), 10))
    # !(test (double 5) 10)
    yield m.eval(S.test(S.double(5), 10))
