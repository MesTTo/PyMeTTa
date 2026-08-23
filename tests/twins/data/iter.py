"""examples/data/iter.metta in Python: an iterator whose state is a number.

`make-nat-iter` answers the starting state, and `iter-next` answers a pair of
the value and the state after it, so stepping three times gives 0, 1, 2. Both
are ordinary compiled functions and the pair is a Python tuple. The original's
`let*` chain binds `$X` to `$N` before answering it, which is an alias with
nothing to name, so the body here is the pair itself.

Stepping is where the twin reads better than the original. The example writes
each step out and DESTRUCTURES the answer inside a `let*`,
`(($x1 $it1) (iter-next $it))`, a pattern binding a compiled body has no form
for yet (friction, P14.4). Out here the answer is an expression and Python
unpacks it, so three steps are a loop rather than three copies of one line.
"""

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Step a natural-number iterator three times and read off the values."""

    @m.define
    def make_nat_iter():                  # (= (make-nat-iter) 0)
        return 0

    @m.define
    def iter_next(n):                     # (= (iter-next $N)
        return (n, n + 1)                 #    (let* (($X $N) ($Next (+ $N 1))) ($X $Next)))

    state, seen = make_nat_iter().one(), []
    for _ in range(3):
        value, state = iter_next(state).one()   # ($x1 $it1), then ($x2 $it2), then ($x3 $it3)
        seen.append(value)

    assert seen == [0, 1, 2]              # ($x1 $x2 $x3) is (0 1 2)
