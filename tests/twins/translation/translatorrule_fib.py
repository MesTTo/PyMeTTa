"""examples/translation/translatorrule_fib.metta in Python: a rule that inlines a call.

`compilefib` is an ordinary definition until it is registered as a translator
rule; from then on `(compilefib 10)` is expanded and evaluated while `smartfun`
is being compiled, so the multiplication that uses it starts from 55 rather
than computing it per call.

The accumulator pair is at the container door for two reasons at once. Its name
is hyphenated, and a compiled body resolves a free name EXACTLY as written, so
no body reaches `fib-tr`; and its guard is MeTTa's own `(== $n 0)`, where
Python's `==` in a compiled body lowers to a host crossing rather than to that
term (residue, P14.4). Everything above it compiles: `compilefib` and
`smartfun` name functions the engine knows, which is what the free names below
are.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Define a tail-recursive fib, then inline one call to it at compile time."""
    fib_tr = S["fib-tr"]

    # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
    m += equation(fib_tr(V.n, V.a, V.b)).to(
        S["if"](S["=="](V.n, 0), V.a, fib_tr(V.n - 1, V.b, V.a + V.b))  # rung: a hyphenated head and MeTTa's own == are both out of the compiled subset
    )
    # (= (fib $n) (fib-tr $n 0 1))
    m += equation(S.fib(V.n)).to(fib_tr(V.n, 0, 1))

    @m.define
    def compilefib(n):
        return fib(n)  # noqa: F821  -- a free name in a compiled body is resolved against the engine's registry, where `fib` now is

    # Can be left out, but then `smartfun` recomputes fib(10) on every call.
    m.fn.add_translator_rule(S.compilefib)

    @m.define
    def smartfun(b):
        # compilefib is a rule now, so this call is expanded and evaluated
        # while THIS definition is compiled, never per call.
        return compilefib(10) * b

    assert smartfun(42).one() == 2310
