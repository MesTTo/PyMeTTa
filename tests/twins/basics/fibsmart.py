"""examples/basics/fibsmart.metta in Python: the accumulator fib.

Two equations by one decorator, and the second one shows how a compiled body
reaches a sibling whose MeTTa name is not its Python name. No Python
identifier carries a hyphen, so `def fib_tr` is installed as `fib-tr` by the
naming ladder's own underscore map, and nothing has to say that name twice.
`fib`'s body then CALLS the Python object, and the compiler emits the MeTTa
name that object was installed under, so the stored equation is the
original's.

Compiled-body equality lowers to the engine's `==`, so `fib-tr`'s stored body
matches the original equation as well.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
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
