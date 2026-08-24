"""Purpose: examples/libraries/patrick_iterate_quad.metta in Python: a triangular walk under iterate.

The step carries a triple, (t i sum), and walks the lower triangle of a
thousand-by-thousand grid: when i reaches t the row is finished, so t advances
and i restarts, and otherwise i advances. `iterate` runs it n(n+1)/2 times and
`last` takes the final state; a compiled body says both through the STATIC `fn`
namespace and passes the step by its `S` name, because the step is data there.

`quad-step` stays at the container door, and that is the residue entry this
file carries: its head destructures its second argument, where a decorated
function's parameters are always plain variables.

Inside that built body the conditional is `if_`, the keyword builder with the
engine's own two-or-three arity, and the comparison is `S.eq`, the operator's
WORD. Both are what a STORED equation needs: Python's conditional expression
evaluates rather than building, and `V.i == V.t` is Python's own structural
equality between two variables, which is False. The arithmetic around them is
Python's own, because an operator with a VARIABLE operand builds the term.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation, fn, if_

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Sum t*i over the lower triangle of a thousand rows."""
    m.fn["import!"](m, S.library(S["lib_patrick"]))

    m += equation(S.quad_step(V.dummy, Expression((V.t, V.i, V.sum)))).to(
        if_(
            S.eq(V.i, V.t),
            Expression((V.t + 1, 1, V.sum + V.t * V.i)),
            Expression((V.t, V.i + 1, V.sum + V.t * V.i)),
        )
    )

    @m.define
    def quad_sum(n):
        # (= (quad-sum $n) (last (iterate 0 (/ (* $n (+ $n 1)) 2) (1 1 0) quad-step)))
        return fn.last(fn.iterate(0, n * (n + 1) / 2, (1, 1, 0), S.quad_step))

    assert quad_sum(1000) == [125417041750]
