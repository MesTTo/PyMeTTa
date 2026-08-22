"""The Python twin of examples/libraries/he_evaluation.metta.

One evaluation step, an evaluation in a named space, an explicit chain, and
mapping a unit-answering operation over an expression.

`double` is authored as the Python function it is. `(* $x 2)` inside the chain
takes a VARIABLE, so Python's own `*` builds that term; `(+ 5 5)` and `(+ 2 3)`
take two ground numbers, where Python's `+` is arithmetic and answers the value
before any term exists, so their heads are named instead.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11926 to 13555, +1629 (+13.66%), by the P14
#: twin-style rewrite: the equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom, and the compile costs
#: 1,629 inferences once. Prior: ADDED 2026-08-22 at 11926 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 13555

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    @m.define
    def double(x):
        # (= (double $x) (+ $x $x))
        return x + x

    # !(test (eval (double 5)) 10)
    yield m.eval(S.test(S.eval(S.double(5)), 10))

    # !(test (evalc (+ 5 5) &self) 10)
    yield m.eval(S.test(S.evalc(S["+"](5, 5), S["&self"]), 10))

    # !(test (chain (+ 2 3) $x (* $x 2)) 10)
    yield m.eval(S.test(S.chain(S["+"](2, 3), V.x, V.x * 2), 10))

    # println! answers the UNIT value, which is what the specification types it
    # with, so mapping it over six items answers six units rather than six trues.
    # !(test (for-each-in-atom (1 3 5 62 2 5) println!)
    #        (() () () () () ()))
    yield m.eval(
        S.test(
            S["for-each-in-atom"]((1, 3, 5, 62, 2, 5), S["println!"]),
            ((), (), (), (), (), ()),
        )
    )
