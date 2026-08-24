"""examples/translation/translatorrule_fib.metta in Python: a rule that inlines a call.

`compilefib` is an ordinary definition until it is registered as a translator
rule; from then on `(compilefib 10)` is expanded and evaluated while `smartfun`
is being compiled, so the multiplication that uses it starts from 55 rather
than computing it per call.

Every one of the four is a compiled function now, including the accumulator
pair. Its MeTTa name is hyphenated and its Python name is not, which is one
declaration said once: rung 4's map turns `fib_tr` into `fib-tr` at the head
and resolves the recursive call in the body the same way. Its guard is
Python's own `==`, which the engine executes natively for wire values, so the
comparison never leaves the engine.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1


def twin(m):
    """Define a tail-recursive fib, then inline one call to it at compile time."""

    @m.define
    def fib_tr(n, a, b):                  # (= (fib-tr $n $a $b)
        if n == 0:                        #    (if (== $n 0) $a
            return a                      #        (fib-tr (- $n 1) $b (+ $a $b))))
        return fib_tr(n - 1, b, a + b)

    @m.define
    def fib(n):                           # (= (fib $n) (fib-tr $n 0 1))
        return fib_tr(n, 0, 1)

    @m.define
    def compilefib(n):                    # (= (compilefib $n) (fib $n))
        return fib(n)

    # Can be left out, but then `smartfun` recomputes fib(10) on every call.
    m.fn.add_translator_rule(S.compilefib)   # (add-translator-rule! compilefib)

    @m.define
    def smartfun(b):                      # (= (smartfun $b) (* (compilefib 10) $b))
        # compilefib is a rule now, so this call is expanded and evaluated
        # while THIS definition is compiled, never per call.
        return compilefib(10) * b

    assert smartfun(42).one() == 2310     # [2310]
