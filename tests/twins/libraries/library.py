"""The Python twin of examples/libraries/library.metta.

The smallest library import there is, plus one call into what it brought.

`(+ 1)` is `+` applied to ONE argument, which is a partial application and not
something a Python operator can build, since `1 + something` needs the
something, so the head is named and called with the one argument it takes.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 151231 to 151231, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 151231 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 151231

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_roman))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_roman)))

    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(S.test(S["map-flat"](S["+"](1), (1, 2, 3)), (2, 3, 4)))
