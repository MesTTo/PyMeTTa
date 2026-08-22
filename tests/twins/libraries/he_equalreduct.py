"""The Python twin of examples/libraries/he_equalreduct.metta.

Identity, alpha-equality, and the equality-guarded branch.

`(= (add 1 2) 3)` is an equation whose head is all literals, and a literal
parameter default IS the head pattern for that position, so the decorator writes
it whole and the parameters never appear in the equation. The underscores say
that to a Python reader as well.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9738 to 11367, +1629 (+16.73%), by the P14
#: twin-style rewrite: the literal-headed equation (= (add 1 2) 3) is now
#: compiled from Python syntax by @m.define, whose literal parameter defaults
#: ARE the head patterns, instead of added as an already-built atom. Prior:
#: ADDED 2026-08-22 at 9738 by the wave-3 libraries baseline, which recorded
#: no cause.
BUDGET = 11367


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    @m.define(name="add")
    def add_one_two(_x=1, _y=2):
        # (= (add 1 2) 3)
        return 3

    # !(test (id 5) 5)
    yield m.eval(S.test(S.id(5), 5))

    # !(test (=alpha (Father $X) (Father $Y)) True)
    yield m.eval(S.test(S["=alpha"](S.Father(V.X), S.Father(V.Y)), TRUE))
    # !(test (=alpha (Father $X) (Son $X)) False)
    yield m.eval(S.test(S["=alpha"](S.Father(V.X), S.Son(V.X)), FALSE))

    # !(test (if-equal 1 1 "Equal" "Not Equal") "Equal")
    yield m.eval(
        S.test(S["if-equal"](1, 1, val("Equal"), val("Not Equal")), val("Equal"))
    )
