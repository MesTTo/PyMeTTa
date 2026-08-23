"""examples/data/iter.metta in Python: an iterator whose state is a number.

`make-nat-iter` answers the state, and `iter-next` answers a pair of the value
and the next state, so stepping it three times gives 0, 1, 2. Both are ordinary
compiled functions: the `let*` chain in the original IS the two assignments in
`iter_next`'s body, and the pair it answers is a Python tuple.

Stepping is where the twin reads better than the original. The example's own
`let*` DESTRUCTURES each answer, `(($x1 $it1) (iter-next $it))`, which a
compiled body cannot spell today (filed as friction); out here the answer is an
expression and Python unpacks it, which is the same act with no construct to
learn.
"""

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Step a natural-number iterator three times and read off the values."""

    @m.define(name="make-nat-iter")
    def make_nat_iter():
        return 0

    @m.define(name="iter-next")
    def iter_next(n):
        value = n
        following = n + 1
        return (value, following)

    start = make_nat_iter().one()
    first, after_first = iter_next(start).one()
    second, after_second = iter_next(after_first).one()
    third, _ = iter_next(after_second).one()

    assert (first, second, third) == (0, 1, 2)
