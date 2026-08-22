"""examples/spaces/inherited_spaces.metta in Python: child-first reads, front-only writes.

A child space reads through its parent and writes only into itself. One
conjunction joins a parent fact to a child fact, because each conjunct is
matched through the whole read chain; same-shaped facts come back child first;
and neither write reached the parent.

The original names the child `&family-child` so its later forms can address it.
Nothing here needs the name: `m.new_space(inherits=parent)` answers the HANDLE,
and every door the example uses hangs off that handle, so the anonymous space
is not a compromise but the point (the named form has no Python door, residue
P14.10).

One claim keeps the engine's own function. `len(space)` and iterating it both
answer the whole READ CHAIN, six atoms here, where `(space-atom-count ...)`
answers the writable FRONT STORE, three, which is the boundary this example
exists to draw [measured 2026-08-22; filed as residue against P14.10 and
reported to the integrator]. The Python container protocol is self-consistent,
len and iteration agreeing, so the gap is a missing front-store door rather
than a wrong count.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4780 to 1528, -3252 (-68.0%), by the twin contract
#: change: six `(test (collapse (match ...)) ...)` terms became six Python
#: `assert`s over the subscript door, so `test` and `collapse` left the engine
#: six times while the five matches they wrapped and the one count stayed in
#: it, along with the six writes and the space creation. Against the example's
#: 14263 the ratio is 0.1071.
#: Prior: 4780, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1528


def twin(m):
    """Fill a parent and a child, then read the chain from both ends."""
    parent = m.space("&family-parent")
    parent += S.edge(S.a, S.b)
    parent += S["parent-only"](S.kept)
    parent += S.layer(S.parent)

    child = m.new_space(inherits=parent)
    child += S.edge(S.b, S.c)
    child += S["child-only"](S.local)
    child += S.layer(S.child)

    # One conjunction joins a parent fact to a child fact, because each
    # conjunct is matched through the whole read chain.
    assert [(row.x, row.z) for row in child[S.edge(V.x, V.y), S.edge(V.y, V.z)]] == [
        (S.a, S.c)
    ]

    # Same-shaped facts pin child-first reads without relying on clause order
    # across different arities.
    assert [row.x for row in child[S.layer(V.x)]] == [S.child, S.parent]
    assert m.fn("space-atom-count")(S[child.space_name]) == 3

    # Writes never mutate an ancestor: the parent keeps what it had, the child
    # can read it, and the parent cannot read the child.
    assert [row.x for row in parent[S["parent-only"](V.x)]] == [S.kept]
    assert [row.x for row in child[S["parent-only"](V.x)]] == [S.kept]
    assert not parent[S["child-only"](V.x)]
