"""The Python twin of examples/libraries/test_memo_same_name_multi_arity.metta.

One name at two arities, each with its own cache, memoized one at a time.

`mix` at arity 1 is written by `@m.define`; arity 2 is written at the container
door because a SECOND `@m.define` under one MeTTa name raises IndexError from
the twin dispatcher rather than defining another arity, which the residue table
records against P14.4.
"""

from petta import S, V, equation, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 133122 to 134736, +1614 (+1.21%), by the P14
#: twin-style rewrite: the arity-1 equation is now compiled from Python
#: syntax by @m.define instead of added as an already-built atom, and the
#: compile costs 1,614 inferences once. Prior: ADDED 2026-08-22 at 133122 by
#: the wave-3 libraries baseline, which recorded no cause.
BUDGET = 134736


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """

    @m.define(name="mix")
    def mix_one(x):
        # (= (mix $x) (+ $x 1))
        return x + 1

    # (= (mix $x $y) (+ $x $y))
    m += equation(S.mix(V.x, V.y)).to(V.x + V.y)

    # !(import! &self (library lib_memo))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))

    # !(memoize mix 1)
    yield m.eval(S.memoize(S.mix, 1))
    # !(test (is-memoized mix 1) true)
    yield m.eval(S.test(S["is-memoized"](S.mix, 1), TRUE))
    # !(test (is-memoized mix 2) false)
    yield m.eval(S.test(S["is-memoized"](S.mix, 2), FALSE))

    # !(test (mix 5) 6)
    yield m.eval(S.test(S.mix(5), 6))
    # !(test (mix 5) 6)
    yield m.eval(S.test(S.mix(5), 6))

    # !(test (mix 3 4) 7)
    yield m.eval(S.test(S.mix(3, 4), 7))
    # !(test (mix 3 4) 7)
    yield m.eval(S.test(S.mix(3, 4), 7))

    # !(memoize mix 2)
    yield m.eval(S.memoize(S.mix, 2))
    # !(test (is-memoized mix 2) true)
    yield m.eval(S.test(S["is-memoized"](S.mix, 2), TRUE))
    # !(test (mix 8 9) 17)
    yield m.eval(S.test(S.mix(8, 9), 17))
    # !(test (mix 8 9) 17)
    yield m.eval(S.test(S.mix(8, 9), 17))
