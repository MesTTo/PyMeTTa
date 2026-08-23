"""examples/functions/multicall.metta in Python: one head, two answers.

Both equations answer, so `mycalc(1, 2)` is `[3, -1]` rather than either of
them. That is what a generator says: a definition whose body is a flat
sequence of independent yields stores ONE EQUATION PER YIELD, so the two
alternatives are two atoms under one head, dispatch-visible to `match`,
exactly as the original writes them.

Nothing else is needed. Calling the decorated function answers the lazy view
of its answers, and comparing that view to a list states the multiplicity as
well as the values.
"""

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Two alternatives for one head, and the answers both of them give."""
    @m.define
    def mycalc(x, y):
        # (= (mycalc $x $y) (+ $x $y))
        yield x + y
        # (= (mycalc $x $y) (- $x $y))
        yield x - y

    assert mycalc(1, 2) == [3, -1]
