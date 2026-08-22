"""The Python twin of examples/libraries/he_quoting.metta.

quote holds a term unevaluated, unquote runs it, and noreduce-eq compares two
terms without reducing either.

`quote` is an ordinary symbol typed `(-> Atom Atom)`, so calling it builds the
term the same way calling any other head does. The arithmetic inside it is over
two ground numbers, where Python's own `+` is arithmetic and answers 3 before
any term exists, so `(+ 1 2)` names its head instead.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12127 to 12127, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 12127 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 12127

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(test (quote (+ 1 2)) (quote (+ 1 2)))
    yield m.eval(S.test(S.quote(S["+"](1, 2)), S.quote(S["+"](1, 2))))

    # !(test (eval (+ 1 2)) 3)
    yield m.eval(S.test(S.eval(S["+"](1, 2)), 3))

    # !(test (unquote (quote (+ 1 2))) 3)
    yield m.eval(S.test(S.unquote(S.quote(S["+"](1, 2))), 3))

    # !(test (repr (unquote 42)) "(unquote 42)")
    yield m.eval(S.test(S.repr(S.unquote(42)), val("(unquote 42)")))

    # !(test (noreduce-eq (+ 1 2) (+ 1 2)) True)
    yield m.eval(S.test(S["noreduce-eq"](S["+"](1, 2), S["+"](1, 2)), TRUE))

    # !(test (noreduce-eq (+ 1 2) 3) False)
    yield m.eval(S.test(S["noreduce-eq"](S["+"](1, 2), 3), FALSE))
