"""examples/data/mettaset.metta in Python: a nondeterministic write.

The original builds ONE expression whose parts are superposed, so
`(cons set (superpose (...)))` is eight atoms rather than one and `add-atom`
receives every one of them. Python's own word for a fan-out is the
comprehension, and the write door takes what it yields: `space += <iterable of
atoms>` streams the tuples in as facts, one atom each.

Reading them back is the subscript door, one pattern, and the answers arrive in
the order they were written.
"""

from metta import S, V


def twin(m):
    """Write eight facts from three groups, then read them back."""
    members = {1: (S.a, S.b, S.c), 2: (S.d, S.e, S.f), 3: (S.a, S.b)}
    pairs = [(key, value) for key, values in members.items() for value in values]

    m += [(S.set, key, value) for key, value in pairs]   # (add-atom &self (set $x $y)), eight times

    assert [(row.x, row.y) for row in m[S.set(V.x, V.y)]] == pairs
    #  ((set 1 a) (set 1 b) (set 1 c) (set 2 d) (set 2 e) (set 2 f) (set 3 a) (set 3 b))


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
BUDGET = 259
