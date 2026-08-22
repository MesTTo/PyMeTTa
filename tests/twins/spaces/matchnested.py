"""examples/spaces/matchnested.metta in Python: a match inside a match.

Four friendships go in; for each one, a second match looks for a friendship
starting where it ends, records the pair as `transitive` and deletes both links
it used. Two chains survive that walk, `tim tom tam` and `sim som sam`.

The nesting is Python's own: a query answers a materialised view, so the outer
`for` walks all four rows no matter what the inner body writes, which is the
same snapshot MeTTa's `match` takes. matchnested2.py is the sibling that says
the identical thing with the comma join instead, and the difference between the
two files is exactly the difference between the two examples.

`hide` is the original's output silencer, `(= (hide $1) (empty))`, and it
compiles: `empty()` is an engine function and a body that answers nothing
prunes its branch. Nothing needs silencing here, so it is checked once for what
it does and the rewriting below is written out.
"""

from petta import S, V, order_key

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5150 to 3144, -2006 (-39.0%), by the twin contract
#: change: the nested `(match ... (match ... (add-atom ...)))` term became a
#: nested Python loop over two subscript queries, and the closing
#: `(test (msort (collapse (match ...))) ...)` became one `assert`, so `test`,
#: `msort` and `collapse` left the engine while every write, removal and match
#: stayed in it. Against the example's 10246 the ratio is 0.3069.
#: Prior: 5150, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3144

#: The four friendships the original stores, in its own order.
FRIENDS = [(S.tim, S.tom), (S.tom, S.tam), (S.sim, S.som), (S.som, S.sam)]


def twin(m):
    """Store four friendships, then rewrite every chain into one atom."""

    @m.define
    def hide(_x):
        # (= (hide $1) (empty)): a body that answers nothing prunes.
        return empty()  # noqa: F821

    assert hide(S.anything) == []

    for left, right in FRIENDS:
        m += S.friend(left, right)

    for outer in m[S.friend(V.a, V.b)]:
        for inner in m[S.friend(outer.b, V.c)]:
            m += S.transitive(outer.a, outer.b, inner.c)
            m -= S.friend(outer.a, outer.b)
            m -= S.friend(outer.b, inner.c)

    chains = [S.transitive(row.a, row.b, row.c) for row in m[S.transitive(V.a, V.b, V.c)]]
    assert sorted(chains, key=order_key) == [
        S.transitive(S.sim, S.som, S.sam),
        S.transitive(S.tim, S.tom, S.tam),
    ]
