"""examples/basics/identity.metta in Python: square a number, check the answer.

The example defines `(= (f $x) (* $x $x))` and asserts `(f 1)` is 1. Here the
definition is an ordinary Python function the engine compiles, and the claim
is Python's own `assert`.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Define the square, then check it."""
    @m.define
    def f(x):
        return x * x

    assert f(1) == [1]
