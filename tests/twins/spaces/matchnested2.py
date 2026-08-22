"""examples/spaces/matchnested2.metta in Python: the join, not the nesting.

The same four friendships and the same two chains as matchnested.py, asked for
in one question instead of two: `(, (friend $1 $2) (friend $2 $3))` is a
conjunction, and the comma inside a subscript is Python's own spelling of it,
`m[S.friend(V.a, V.b), S.friend(V.b, V.c)]`.

So the pair of examples reads in Python exactly as it reads in MeTTa: nested
`for` loops there, one join here, the same answers either way. A join answers
each solution once, with all three names bound, which is why this file's body
is a single loop with no inner query in it.
"""

from petta import S, V, order_key

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5148 to 2936, -2212 (-43.0%), by the twin contract
#: change: the `(match &self (, ...) (add-atom ...))` term became a Python
#: loop over one joined subscript query, and the closing
#: `(test (msort (collapse (match ...))) ...)` became one `assert`, so `test`,
#: `msort` and `collapse` left the engine while the join, the writes and the
#: removals stayed in it. Against the example's 10036 the ratio is 0.2925.
#: Prior: 5148, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 2936

#: The four friendships the original stores, in its own order.
FRIENDS = [(S.tim, S.tom), (S.tom, S.tam), (S.sim, S.som), (S.som, S.sam)]


def twin(m):
    """Store four friendships, then rewrite every chain the join finds."""

    @m.define
    def hide(_x):
        # (= (hide $1) (empty)): a body that answers nothing prunes.
        return empty()  # noqa: F821

    assert hide(S.anything) == []

    for left, right in FRIENDS:
        m += S.friend(left, right)

    for row in m[S.friend(V.a, V.b), S.friend(V.b, V.c)]:
        m += S.transitive(row.a, row.b, row.c)
        m -= S.friend(row.a, row.b)
        m -= S.friend(row.b, row.c)

    chains = [S.transitive(row.a, row.b, row.c) for row in m[S.transitive(V.a, V.b, V.c)]]
    assert sorted(chains, key=order_key) == [
        S.transitive(S.sim, S.som, S.sam),
        S.transitive(S.tim, S.tom, S.tam),
    ]
