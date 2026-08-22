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
building the term an equation has to store.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 35565297 to 35564694, -603 (-0.00%), by the
#: idiomatic rewrite: the one `test` wrapper left the engine for `assert`;
#: the triangular walk over half a million steps is the whole cost. Measured
#: min-of-three with the MORK backend linked into this worktree, which the
#: earlier figure may not have been. Prior: 35565297 was the last figure for
#: the generator twin that yielded `m.eval(S.test(...))` once per runnable
#: form.
BUDGET = 35564694


def twin(m):
    """Sum t*i over the lower triangle of a thousand rows."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_patrick)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S["quad-step"](V.dummy, Expression((V.t, V.i, V.sum)))).to(
        S["if"](  # rung: this `if` is the BODY of a stored equation, and Python's conditional expression evaluates rather than building the term the equation has to hold
            S["=="](V.i, V.t),
            Expression((V.t + 1, 1, V.sum + V.t * V.i)),
            Expression((V.t, V.i + 1, V.sum + V.t * V.i)),
        )
    )
    m += equation(S["quad-sum"](V.n)).to(
        S.last(S.iterate(0, V.n * (V.n + 1) / 2, (1, 1, 0), S["quad-step"]))
    )

    assert m.fn("quad-sum")(1000) == 125417041750
