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

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5783 to 3546, -2237 (-38.68%), by the twin-shape
#: rewrite: the `test` wrapper left the engine for `assert`, and the `let*`
#: chain that destructured each answer left it too: out here the answer is an
#: expression and Python unpacks it. Against the example's 7823 the ratio is
#: 0.4533 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/iter.metta`]. Prior: RE-PINNED at 5783 by the wave-4 idiom
#: rewrite.
BUDGET = 3546


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

    start = make_nat_iter()[0]
    first, after_first = iter_next(start)[0]
    second, after_second = iter_next(after_first)[0]
    third, _ = iter_next(after_second)[0]

    assert (first, second, third) == (0, 1, 2)
