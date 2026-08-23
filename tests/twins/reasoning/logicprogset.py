"""Purpose: examples/reasoning/logicprogset.metta in Python: a set built by checking it.

`myf` says what a two-element set containing `a` and `b` is, and the example
then asks for one. Nothing constructs it: the first two conjuncts BIND `$M` by
membership and the third fixes its size, so the answer falls out of the search.

The equation stays at the container door because MeTTa's `and` is not Python's.
Python's `and` short-circuits on truthiness and lowers to a `let*`-then-`if`
chain; `(and (member a $M) (member b $M))` is a generate-and-test in which the
first conjunct binds for the second, and that binding IS the example. So the
term is built as it is, with `&` for `and` and `.eq` for the equality term,
since `==` between atoms is Python's own structural equality.

The claim is `solve`, which is the relational `let`: the subject is evaluated,
its answer is unified with the pattern, and the subject's own variables come
back as bindings. That is what carries `$M` out, where an evaluation would
answer values.
"""

from metta import TRUE, S, V, equation, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def twin(m):
    """Say what the set is, then let the search find one."""
    m += equation(S.myf(V.M)).to(
        fn.member(S.a, V.M) & fn.member(S.b, V.M)
        & fn.size_atom(V.M).eq(2)  # rung: `len()` needs a value; $M is a variable the search has not bound yet
    )

    # `(a b)` is the two-member SET the search found. Calling the head is the
    # shorter spelling of that same two-element atom.
    assert m.solve(TRUE, fn.once(S.myf(V.M))).M == S.a(S.b)
