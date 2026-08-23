"""Purpose: examples/spaces/inherited_spaces.metta in Python: child-first reads, front-only writes.

A child space reads through its parent and writes only into itself. One
conjunction joins a parent fact to a child fact, because each conjunct is
matched through the whole read chain; same-shaped facts come back child first;
and neither write reached the parent.

The original names the child `&family-child` so its later forms can address it.
Nothing here needs the name: `petta.space(inherits=parent)` answers the HANDLE,
and every door the example uses hangs off that handle, so the anonymous space
is not a compromise but the point (the named form has no Python door, residue
P14.10). PERFECT: `petta.space("&family-child", inherits=parent)`, the creation
options applying to a named space as well as an anonymous one.

One claim keeps the engine's own function. `len(space)` and iterating it both
answer the whole READ CHAIN, six atoms here, where `(space-atom-count ...)`
answers the writable FRONT STORE, three, which is the boundary this example
exists to draw [measured 2026-08-22; filed as residue against P14.10 and
reported to the integrator]. The Python container protocol is self-consistent,
len and iteration agreeing, so the gap is a missing front-store door rather
than a wrong count. PERFECT: `len(child.front)`, or a declared capacity view, so
the question the example is about has a Python spelling. The handle goes into
the call as an ordinary operand.
"""

import petta
from petta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fill a parent and a child, then read the chain from both ends."""
    parent = petta.space("&family-parent")
    parent += S.edge(S.a, S.b)
    parent += S["parent-only"](S.kept)
    parent += S.layer(S.parent)

    child = petta.space(inherits=parent)
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
    assert m.fn["space-atom-count"](child).one() == 3

    # Writes never mutate an ancestor: the parent keeps what it had, the child
    # can read it, and the parent cannot read the child.
    assert [row.x for row in parent[S["parent-only"](V.x)]] == [S.kept]
    assert [row.x for row in child[S["parent-only"](V.x)]] == [S.kept]
    assert not parent[S["child-only"](V.x)]
