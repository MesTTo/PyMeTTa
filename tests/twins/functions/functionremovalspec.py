"""examples/functions/functionremovalspec.metta in Python: removal under specialization.

`f` applies its argument, so a call `(f g)` SPECIALIZES on `g`; removing one
of `f`'s two clauses must leave the specialized call working over the clause
that remains, and putting the clause back must bring its answer back.

Both definitions are decorated Python functions. `g` is a computation; `f`'s
two clauses are ALTERNATIVES that both answer, which a generator body says
directly, one stored equation per yield. Naming the equation the yield stored
is what lets `-=` and `+=` take it as the atom it is.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Remove one clause of a specialized function, then put it back."""

    @m.define
    def g(x):
        # (= (g $x) (+ $x 1))
        return x + 1

    @m.define
    def f(g):
        # (= (f $g) ($g 1))
        yield (g, 1)
        # (= (f $g) ($g 2))
        yield (g, 2)

    one = equation(S.f(V.g)).to((V.g, 1))

    assert m.eval(S.f(S.g)) == [2, 3]

    m -= one
    # The specialized call still runs, over the one clause left.
    assert m.eval(S.f(S.g)) == [3]

    m += one
    assert m.eval(S.f(S.g)) == [3, 2]
