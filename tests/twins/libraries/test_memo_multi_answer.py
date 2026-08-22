"""The Python twin of examples/libraries/test_memo_multi_answer.metta.

A memoized function with two answers gives both, on the call that misses and
on the call that hits.

`yield` IS nondeterminism, so the source's two equations for one head are one
`@m.define` generator whose body superposes the two alternatives. A second
decorator under the same head would REPLACE the first rather than stack beside
it, which is what makes the generator the spelling here rather than a taste;
the residue table records that against P14.4. The definition is installed ahead
of the runnable forms for the loader-ordering reason recorded on the same row.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 128335 to 129174, +839 (+0.65%), by the P14 twin-
#: style rewrite: the two equations for one head become one @m.define
#: generator whose body superposes the alternatives, and the compile replaces
#: one of the two container-door atom adds. Prior: ADDED 2026-08-22 at 128335
#: by the wave-3 libraries baseline, which recorded no cause.
BUDGET = 129174


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define
    def choose(x):
        # (= (choose $x) $x)
        # (= (choose $x) (Pair $x $x))
        yield x
        yield Pair(x, x)  # noqa: F821  -- a capitalized free name is a MeTTa data constructor, which is how the compiled subset spells one

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # Enable memoization for a function that returns multiple answers.
    # !(memoize choose)
    yield m.eval(S.memoize(S.choose))

    # First call misses, second hits from cache.
    # !(test (choose 7) (7 (Pair 7 7)))
    yield m.eval(S.test(S.choose(7), (7, S.Pair(7, 7))))
    # !(test (choose 7) (7 (Pair 7 7)))
    yield m.eval(S.test(S.choose(7), (7, S.Pair(7, 7))))
