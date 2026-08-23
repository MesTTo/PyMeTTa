"""examples/basics/fibsmart.metta in Python: the accumulator fib.

Two equations by one decorator, and the second one shows how a compiled body
reaches a sibling whose MeTTa name is not its Python name. No Python
identifier carries a hyphen, so `def fib_tr` is installed as `fib-tr` by the
naming ladder's own underscore map, and nothing has to say that name twice.
`fib`'s body then CALLS the Python object, and the compiler emits the MeTTa
name that object was installed under, so the stored equation is the
original's.

`fib-tr`'s stored body differs from the original's in one place: a compiled
body's `==` lowers to the prelude's `py-eq` where the original writes MeTTa's
`(== $n 0)`. The residue table records that against P14.4.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Define the accumulator fib and its entry point, then run it."""
    @m.define
    def fib_tr(n, a, b):
        # (= (fib-tr $n $a $b) (if (== $n 0) $a (fib-tr (- $n 1) $b (+ $a $b))))
        return a if n == 0 else fib_tr(n - 1, b, a + b)

    # A body calling the definition above it is the ordinary call: `fib_tr` is
    # bound here to the decorated object, and the compiler emits that object's
    # installed MeTTa name, so the stored body is `(fib-tr $n 0 1)` even
    # though the two names differ.
    @m.define
    def fib(n):
        # (= (fib $n) (fib-tr $n 0 1))
        return fib_tr(n, 0, 1)

    assert fib(100) == [354224848179261915075]
