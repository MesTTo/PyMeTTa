"""Purpose: examples/libraries/patrick_iterate_fib.metta in Python: fib by iteration, not recursion.

`iterate` runs a step function n times over a carried state, so the hundredth
Fibonacci number costs a hundred steps rather than a tree of calls. `iterate`
and `first` are lib_patrick's own, and a compiled body says them through the
STATIC `fn` namespace, which is what a body reads for a function it did not
define; the step it PASSES is data, so it takes the `S` door.

`fib-step` stays at the container door, and that is the residue entry this file
carries: its head destructures its second argument, `(fib-step $i ($a $b))`,
where a decorated function's parameters are always plain variables.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Carry a pair a hundred times, then take its first half."""
    m.fn["import!"](m, S.library(S["lib_patrick"]))

    # One step: the pair (a b) becomes (b a+b).
    m += equation(S.fib_step(V.i, Expression((V.a, V.b)))).to(Expression((V.b, V.a + V.b)))

    @m.define
    def fib(n):
        # (= (fib $n) (first (iterate 0 $n (0 1) fib-step)))
        return fn.first(fn.iterate(0, n, (0, 1), S.fib_step))

    assert fib(100) == [354224848179261915075]
