"""Purpose: examples/spaces/catalog.metta in Python: the catalog describes its own kinds.

Every declaration the engine acts on is an atom in the reflection space, and
the SHAPES of those declarations are atoms there too, so one generic checker
guards every write against the standing rows. A third-party kind is the same
machinery: declare its vocabulary and its shape, and from that moment the same
checker guards it.

Which is why this file has no special introspection door in it. The reflection
space is a space, so reading it is `space[pattern]` and extending it is
`space += row`, exactly as for any other knowledge, and that IS the example's
point made in Python. `petta.reflection` is the handle itself, not a name.

`&rows` appears inside a declaration as the context the freshness claim is
about, and it appears there as the HANDLE: a space is an ordinary term operand,
so `petta.space("&rows")` goes straight into the row it is the subject of.
"""

import petta
from petta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):  # noqa: ARG001  -- the catalog lives in the reflection space; the default handle stays untouched
    """Read four shipped catalog rows, then declare a kind of your own."""
    reflection = petta.reflection

    # The fidelity vocabulary is the four words the handles router acts on.
    assert [
        (row.a, row.b, row.c, row.d)
        for row in reflection[S.vocabulary(S.fidelity, V.a, V.b, V.c, V.d)]
    ] == [(S.Exact, S.Partial, S.Sound, S.Refuse)]

    # The handles kind row is the shape every (handles ...) declaration fits.
    assert [
        row.claim for row in reflection[S.kind(S.handles, V.ctx, V.entry, V.claim, V.det)]
    ] == [S["one-of"](S.fidelity)]

    # Orderedness is a claim on a semiring value, which is what (top k ...)
    # consults rather than a word list compiled into the engine.
    assert [row.p for row in reflection[S.claim(S.semiring, S.ranked, V.p)]] == [S.ordered]

    # A third-party kind is the same machinery: declare its vocabulary and its
    # shape, and the same checker guards it.
    rows = petta.space("&rows")
    reflection += (S.vocabulary, S["freshness-level"], S.live, S.cached, S.stale)
    reflection += (
        S.kind,
        S.freshness,
        S.symbol,
        S.pattern,
        S["one-of"](S["freshness-level"]),
    )
    reflection += (S.freshness, rows, S.edge(V.a, V.b), S.cached)

    assert [
        row.level for row in reflection[S.freshness(rows, V.shape, V.level)]
    ] == [S.cached]

    # (routed-by-shape head) gives the kind the SAME router the shipped
    # handles declarations use, inherited rather than reimplemented.
    reflection += (S["routed-by-shape"], S.freshness)
    assert S["routed-by-shape"](S.freshness) in reflection
