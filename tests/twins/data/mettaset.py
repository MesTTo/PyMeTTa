"""examples/data/mettaset.metta in Python: a nondeterministic write.

The original builds ONE expression whose parts are superposed, so `(cons set
(superpose (...)))` is eight atoms rather than one, and `add-atom` receives
every one of them. In Python the fan-out is a comprehension over the members,
each row a plain tuple that encodes to the expression it names, and the write
door takes them all.

`m.add(*rows)` rather than `space += rows`: a generator or list on the right of
`+=` is stored as ONE atom today, so the iterable pipe the design names is not
open yet (filed as friction). Reading them back is the subscript door, and the
answers come in the order they were written.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3573 to 422, -3151 (-88.19%), by the twin-shape
#: rewrite: the `test` wrapper and the `collapse` under it left the engine
#: for `assert` over rows, and the nondeterministic construction left it
#: entirely: `(cons set (superpose ...))` fanning out into eight atoms is a
#: comprehension over the members, so the engine sees eight writes and one
#: query instead of a superposed let. Against the example's 7144 the ratio is
#: 0.0591 [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/data/mettaset.metta`]. Prior: the file's first pin, uncommented.
BUDGET = 422


def twin(m):
    """Write eight facts from three groups, then read them back."""
    members = {1: (S.a, S.b, S.c), 2: (S.d, S.e, S.f), 3: (S.a, S.b)}

    m.add(*[(S.set, key, value)
            for key, values in members.items()
            for value in values])

    assert [(row.x, row.y) for row in m[S.set(V.x, V.y)]] == [
        (key, value) for key, values in members.items() for value in values
    ]
