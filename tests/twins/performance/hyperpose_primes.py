"""Purpose: examples/performance/hyperpose_primes.metta in Python: branches on real threads.

`hyperpose` fans a list of terms out over worker threads. The first form proves
the plumbing on three numbers, and the two after it race four primality tests,
once to completion and once until the first answer.

Only the first form is answered here. The other two are DECLINED, and the reason
is arithmetic rather than expressive: a thread that is cancelled mid-search
stops at whatever point the scheduler reached, so the inference count is not a
number any twin can pin. The residue records both against P14.14, which owns the
budget laws.

What the answered form shows is the dissolution table three times over: `let` is
an assignment, `collapse` is the answer list `m.hyperpose` already hands back,
and `msort` is `sorted`, because atoms carry the engine's own order.

Both equations are ordinary Python functions under the decorator, and both
equality tests name their head: Python's `==` inside a compiled body lowers to
the prelude's `py-eq`, a host crossing per iteration, where MeTTa's own `==` is
declared `(-> $t $t Bool)` and a compiled `if` emits it bare.
superpose_primes.py beside this file carries the measurement.
"""

from metta import fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. Form 0 runs on real threads besides, so its count is not identical
#: across fresh processes and the re-pin pass owns that decision too
#: [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fan three numbers out over threads, and put the primes back together."""

    @m.define
    def find_divisor(n, test_divisor):
        if test_divisor * test_divisor > n:
            return n
        if fn.eq(0, n % test_divisor):  # rung: `==` lowers to the prelude's `py-eq`, a host crossing per iteration, where the example writes MeTTa's own `==`
            return test_divisor
        return find_divisor(n, test_divisor + 1)

    @m.define(name="prime?")
    def prime(n):
        return fn.eq(n, fn.find_divisor(n, 2))  # rung: the same host crossing, in answer position

    # hyperpose takes its branches through a variable as happily as inline, and
    # the answers come back in whatever order the threads finish.
    xs = (3, 1, 2)
    assert sorted(m.hyperpose(*xs)) == [1, 2, 3]
