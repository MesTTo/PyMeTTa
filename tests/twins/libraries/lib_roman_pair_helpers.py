"""The Python twin of examples/libraries/lib_roman_pair_helpers.metta.

lib_roman's pair helpers: applying a function to one half of a pair, and
flipping the halves.

`inc` is authored as the Python function it is; the pairs are Python tuples,
which is what a MeTTa expression already is.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 152447 to 154076, +1629 (+1.07%), by the P14
#: twin-style rewrite: inc's equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom, and the compile costs
#: 1,629 inferences once. Prior: ADDED 2026-08-22 at 152447 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 154076


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_roman))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))

    @m.define
    def inc(x):
        # (= (inc $x) (+ $x 1))
        return x + 1

    # !(test (first inc (1 9)) (2 9))
    yield m.eval(S.test(S.first(S.inc, (1, 9)), (2, 9)))
    # !(test (second inc (1 9)) (1 10))
    yield m.eval(S.test(S.second(S.inc, (1, 9)), (1, 10)))
    # !(test (flip (left right)) (right left))
    yield m.eval(S.test(S.flip((S.left, S.right)), (S.right, S.left)))
