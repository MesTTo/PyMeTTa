"""examples/basics/fibsmart.metta in Python: the accumulator fib.

Two equations by two doors of the SAME decorator, and the second one shows
how a compiled body reaches a name Python's grammar will not spell.
`fib-tr` is a decorated Python function under `name="fib-tr"`, because no
Python identifier carries a hyphen. `fib`'s body has to CALL it, and a
compiled body resolves a free name through the descent ladder: rung 4 asks
for the exact spelling and then for its underscore-to-hyphen image, so a bare
`fib_tr(...)` would reach `fib-tr`. It does not here, because this file binds
the Python name `fib_tr` to the decorated function, and a host binding of
that spelling deliberately blocks the mapped fallback rather than crossing
the quotation boundary by surprise. So the call descends one more rung, to
the quoted-name escape `S["fib-tr"]`, which is exactly what rung 5 is for and
which stores the original's own equation.

`fib-tr`'s stored body differs from the original's in one place: a compiled
body's `==` lowers to the prelude's `py-eq` where the original writes MeTTa's
`(== $n 0)`. The residue table records that against P14.4.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Define the accumulator fib and its entry point, then run it."""
    @m.define(name="fib-tr")
    def fib_tr(n, a, b):
        # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
        return a if n == 0 else fib_tr(n - 1, b, a + b)

    # DEFECT, and the line below is the workaround. The perfect spelling of a
    # body calling the definition above it is the ordinary call,
    #
    #     return fib_tr(n, 0, 1)
    #
    # and it raises `CompileError: 'fib_tr' is not a parameter of fib, not a
    # function the engine knows`. Rung 4's underscore-to-hyphen map would reach
    # `fib-tr`, but a HOST BINDING of the same spelling blocks the mapped
    # fallback, and `fib_tr` is bound here to the decorated function itself. So
    # a body can never call a sibling whose MeTTa name differs from its Python
    # name by that name, only at rung 5. The resolver should consult a bound
    # `Defined`'s own MeTTa name before treating the binding as opaque host
    # state [measured 2026-08-23 on this worktree; commit=WORKTREE].
    @m.define
    def fib(n):
        # (= (fib $n) (fib-tr $n 0 1))
        return S["fib-tr"](n, 0, 1)

    assert fib(100) == [354224848179261915075]
