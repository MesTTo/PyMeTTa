"""Purpose: examples/spaces/matchnested2.metta in Python: the join, not the nesting.

The same four friendships and the same two chains as matchnested.py, asked for
in one question instead of two: `(, (friend $1 $2) (friend $2 $3))` is a
conjunction, and the comma inside a subscript is Python's own spelling of it,
`m[S.friend(V.a, V.b), S.friend(V.b, V.c)]`.

So the pair of examples reads in Python exactly as it reads in MeTTa: nested
`for` loops there, one join here, the same answers either way. A join answers
each solution once, with all three names bound, which is why this file's body
is a single loop with no inner query in it.

`sorted(atoms)` is `msort`: atoms carry the engine's own elementwise order.
"""

from metta import S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1

#: The four friendships the original stores, in its own order.
FRIENDS = [(S.tim, S.tom), (S.tom, S.tam), (S.sim, S.som), (S.som, S.sam)]


def twin(m):
    """Store four friendships, then rewrite every chain the join finds."""

    @m.define
    def hide(_x):
        # (= (hide $1) (empty)): a body that answers nothing prunes.
        return fn.empty()

    assert hide(S.anything) == []

    for left, right in FRIENDS:
        m += S.friend(left, right)

    for row in m[S.friend(V.a, V.b), S.friend(V.b, V.c)]:
        m += S.transitive(row.a, row.b, row.c)
        m -= S.friend(row.a, row.b)
        m -= S.friend(row.b, row.c)

    chains = [S.transitive(row.a, row.b, row.c) for row in m[S.transitive(V.a, V.b, V.c)]]
    assert sorted(chains) == [
        S.transitive(S.sim, S.som, S.sam),
        S.transitive(S.tim, S.tom, S.tam),
    ]
