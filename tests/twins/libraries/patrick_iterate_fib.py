"""Purpose: examples/libraries/patrick_iterate_fib.metta in Python: fib by iteration, not recursion.

`iterate` runs a step function n times over a carried state, so the hundredth
Fibonacci number costs a hundred steps rather than a tree of calls. `iterate`
and `first` are lib_patrick's own and stay named; both are bound once as
mentions, the way a rule bundle binds the heads it rewrites.

Both equations are at the container door, and both reasons are already in the
residue table. `fib-step`'s head destructures its second argument,
`(fib-step $i ($a $b))`, where a decorated function's parameters are always
plain variables; and `fib`'s body PASSES `fib-step` as data, where a compiled
body resolves a lowercase free name as a function to call, and cannot spell a
hyphen at all.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Carry a pair a hundred times, then take its first half."""
    m.eval(S["import!"](m, S.library(S["lib_patrick"])))

    first, iterate, fib_step = S.first, S.iterate, S["fib-step"]

    # One step: the pair (a b) becomes (b a+b).
    m += equation(fib_step(V.i, Expression((V.a, V.b)))).to(Expression((V.b, V.a + V.b)))
    m += equation(S.fib(V.n)).to(first(iterate(0, V.n, (0, 1), fib_step)))

    assert m.fn.fib(100) == [354224848179261915075]
