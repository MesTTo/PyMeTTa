"""Purpose: examples/libraries/patrick_iterate_quad.metta in Python: a triangular walk under iterate.

The step carries a triple, (t i sum), and walks the lower triangle of a
thousand-by-thousand grid: when i reaches t the row is finished, so t advances
and i restarts, and otherwise i advances. `iterate` runs it n(n+1)/2 times and
`last` takes the final state. Both are lib_patrick's own and stay named.

Both equations are at the container door for the reasons
patrick_iterate_fib gives: `quad-step`'s head destructures its second argument,
and `quad-sum`'s body passes `quad-step` as data.

Inside those built bodies, `==` and `if` are written as heads rather than as
Python punctuation, and that is the deliberate spelling: outside a compiled
body `V.i == V.t` is Python's own structural equality between two variables,
which is False, and Python's conditional expression evaluates rather than
building the term an equation has to store. The arithmetic around them is
Python's own, because an operator with a VARIABLE operand builds the term.
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
    """Sum t*i over the lower triangle of a thousand rows."""
    m.eval(S["import!"](m, S.library(S["lib_patrick"])))

    last, iterate, quad_step = S.last, S.iterate, S["quad-step"]

    m += equation(quad_step(V.dummy, Expression((V.t, V.i, V.sum)))).to(
        S["if"](  # rung: this `if` is the BODY of a stored equation, and Python's conditional expression evaluates rather than building the term the equation has to hold
            S["=="](V.i, V.t),
            Expression((V.t + 1, 1, V.sum + V.t * V.i)),
            Expression((V.t, V.i + 1, V.sum + V.t * V.i)),
        )
    )
    m += equation(S["quad-sum"](V.n)).to(
        last(iterate(0, V.n * (V.n + 1) / 2, (1, 1, 0), quad_step))
    )

    assert m.fn.quad_sum(1000) == [125417041750]
