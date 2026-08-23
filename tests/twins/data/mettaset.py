"""examples/data/mettaset.metta in Python: a nondeterministic write.

The original builds ONE expression whose parts are superposed, so `(cons set
(superpose (...)))` is eight atoms rather than one, and `add-atom` receives
every one of them. In Python the fan-out is a comprehension over the members,
each row a plain tuple that encodes to the expression it names, and the write
door takes them all.

Known issue: the perfect spelling of the write is `space += rows`, the fact-
stream pipe the design names ('anything that yields tuples is a fact stream').
A LIST on the right of `+=` is stored as ONE atom instead, silently, after
which the pattern below answers nothing; a generator raises. `m.add(*rows)`
is written out until `+=` tells a single atom from an iterable of atoms
[measured 2026-08-22, re-measured 2026-08-23]. Reading them back is the
subscript door, and the answers come in the order they were written.
"""

from metta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Write eight facts from three groups, then read them back."""
    members = {1: (S.a, S.b, S.c), 2: (S.d, S.e, S.f), 3: (S.a, S.b)}

    m.add(*[(S.set, key, value)
            for key, values in members.items()
            for value in values])

    assert [(row.x, row.y) for row in m[S.set(V.x, V.y)]] == [
        (key, value) for key, values in members.items() for value in values
    ]
