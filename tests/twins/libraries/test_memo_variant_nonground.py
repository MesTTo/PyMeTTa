"""The Python twin of examples/libraries/test_memo_variant_nonground.metta.

Two non-ground calls that differ only in variable name hit the same cache entry.

Written at the container door on two counts, both recorded against P14.4:
`@m.define` takes a head pattern only as a LITERAL parameter default, so
`(shape-kind (Pair $x $y))` has no decorator spelling; and a compiled body reads
a bare lowercase name as neither a parameter nor a constructor nor a known
function, so the answer `pair` has no spelling in one either.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 126917 to 126917, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: the head pattern and the lowercase answer keep
#: this twin at the container door, and equation(...).to(...) builds the same
#: atom S["="](...) built. Prior: ADDED 2026-08-22 at 126917 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 126917


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # The output depends only on structure, not concrete variable identity.
    # (= (shape-kind (Pair $x $y)) pair)
    m += equation(S["shape-kind"](S.Pair(V.x, V.y))).to(S.pair)

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # Enable memoization for a function called with non-ground inputs.
    # !(memoize shape-kind)
    yield m.eval(S.memoize(S["shape-kind"]))

    # Both non-ground calls with different variable names should return pair.
    # !(test (shape-kind (Pair $a 2)) pair)
    yield m.eval(S.test(S["shape-kind"](S.Pair(V.a, 2)), S.pair))
    # !(test (shape-kind (Pair $b 2)) pair)
    yield m.eval(S.test(S["shape-kind"](S.Pair(V.b, 2)), S.pair))
