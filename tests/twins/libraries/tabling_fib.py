"""The Python twin of examples/libraries/tabling_fib.metta.

Naive exponential fib, declared tabled, so it answers in linear time.

`@m.define` writes the equation and the declaration stays the separate runnable
form the original makes it: `@m.cache` is the shipped one-decorator spelling for
"define and table", but it imports lib_tabling and evaluates `(tabled ...)`
inside itself, and both are forms of this example whose answers the lane
compares. The point the file makes is the ORDER, that a name must exist before
it can be instrumented, and a decorator that does both at once cannot show it.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 81531 to 83268, +1737 (+2.13%), by the P14
#: twin-style rewrite: the equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom. Prior: ADDED
#: 2026-08-22 at 81531 by the wave-3 libraries baseline, which recorded no
#: cause.
BUDGET = 83268


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_tabling))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_tabling)))

    @m.define
    def fib(n):
        # (= (fib $N) (if (< $N 2) $N (+ (fib (- $N 1)) (fib (- $N 2)))))
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    # Declare AFTER defining: tabling instruments the compiled function, so
    # the name is refused loudly while it does not exist yet.
    # !(tabled (fib $N))
    yield m.eval(S.tabled(S.fib(V.N)))

    # !(test (fib 30) 832040)
    yield m.eval(S.test(S.fib(30), 832040))
