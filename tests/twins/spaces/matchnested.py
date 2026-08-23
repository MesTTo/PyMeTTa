"""Purpose: examples/spaces/matchnested.metta in Python: a match inside a match.

Four friendships go in; for each one, a second match looks for a friendship
starting where it ends, records the pair as `transitive` and deletes both links
it used. Two chains survive that walk, `tim tom tam` and `sim som sam`.

The nesting is Python's own: a query answers a materialised view, so the outer
`for` walks all four rows no matter what the inner body writes, which is the
same snapshot MeTTa's `match` takes. matchnested2.py is the sibling that says
the identical thing with the comma join instead, and the difference between the
two files is exactly the difference between the two examples.

`hide` is the original's output silencer, `(= (hide $1) (empty))`, and it
compiles: `fn.empty` names the engine function through the mention door and a
body that answers nothing prunes its branch. Nothing needs silencing here, so
it is checked once for what it does and the rewriting below is written out.

`sorted(atoms)` is `msort`: atoms carry the engine's own elementwise order.
"""

from metta import S, V, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1

#: The four friendships the original stores, in its own order.
FRIENDS = [(S.tim, S.tom), (S.tom, S.tam), (S.sim, S.som), (S.som, S.sam)]


def twin(m):
    """Store four friendships, then rewrite every chain into one atom."""

    @m.define
    def hide(_x):
        # (= (hide $1) (empty)): a body that answers nothing prunes.
        return fn.empty()

    assert hide(S.anything) == []

    for left, right in FRIENDS:
        m += S.friend(left, right)

    for outer in m[S.friend(V.a, V.b)]:
        for inner in m[S.friend(outer.b, V.c)]:
            m += S.transitive(outer.a, outer.b, inner.c)
            m -= S.friend(outer.a, outer.b)
            m -= S.friend(outer.b, inner.c)

    chains = [S.transitive(row.a, row.b, row.c) for row in m[S.transitive(V.a, V.b, V.c)]]
    assert sorted(chains) == [
        S.transitive(S.sim, S.som, S.sam),
        S.transitive(S.tim, S.tom, S.tam),
    ]
