"""The Python twin of examples/libraries/patrick_iterate_fib.metta.

Fibonacci as a fold: `iterate` runs a step function n times over a carried pair.

Both equations stay at the container door, and both reasons are recorded against
P14.4. `fib-step` destructures its second argument IN THE HEAD, and a decorator
takes a head pattern only as a LITERAL parameter default. `fib` then passes
`fib-step` by name, and a compiled body reaches a free name exactly as written,
which leaves a hyphenated MeTTa name unspellable from Python.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 31840 to 31840, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: both equations stay
#: container-door atoms and equation(...).to(...) builds what S["="](...)
#: built. Prior: ADDED 2026-08-22 at 31840 by the wave-3 libraries baseline,
#: which recorded no cause.
BUDGET = 31840


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_patrick))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))

    # (= (fib-step $i ($a $b))
    #    ($b (+ $a $b)))
    m += equation(S["fib-step"](V.i, (V.a, V.b))).to((V.b, V.a + V.b))

    # (= (fib $n)
    #    (first (iterate 0 $n (0 1) fib-step)))
    m += equation(S.fib(V.n)).to(
        S.first(S.iterate(0, V.n, (0, 1), S["fib-step"]))
    )

    # !(test (fib 100) 354224848179261915075)
    yield m.eval(S.test(S.fib(100), 354224848179261915075))
