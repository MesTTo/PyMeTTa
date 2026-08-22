"""examples/basics/fibsmart.metta in Python: the accumulator fib.

Two equations by two doors, and the second door is a real wall rather than a
preference. `fib-tr` is a decorated Python function, because a compiled body
may name ITSELF under either spelling. `fib` cannot be one: its body calls
`fib-tr`, a compiled body resolves a free name EXACTLY, and no Python
identifier is spelled `fib-tr`. So `fib` is written as the alias equation it
is, which is the remedy the compiler's own refusal names.

`fib-tr`'s stored body differs from the original's in one place: a compiled
body's `==` lowers to the prelude's `py-eq` where the original writes MeTTa's
`(== $n 0)`. The residue table records that against P14.4.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8679 to 8050, -629 (-7.2%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, and the call
#: goes through `m.fn("fib")` rather than a built `(test ...)` term.
#: Against the example's 8505 the ratio is 0.9465 [measured 2026-08-22
#: min-of-3, `twin_coverage.py --measure`]. The old figure priced a
#: different program.
BUDGET = 8050


def twin(m):
    """Define the accumulator fib and its entry point, then run it."""
    @m.define(name="fib-tr")
    def fib_tr(n, a, b):
        # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
        return a if n == 0 else fib_tr(n - 1, b, a + b)

    # (= (fib $n) (fib-tr $n 0 1))
    m += equation(S.fib(V.n)).to(S["fib-tr"](V.n, 0, 1))

    assert m.fn("fib")(100) == 354224848179261915075
