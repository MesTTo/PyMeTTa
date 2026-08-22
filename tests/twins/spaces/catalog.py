"""examples/spaces/catalog.metta in Python: the catalog describes its own kinds.

Every declaration the engine acts on is an atom in the reflection space, and
the SHAPES of those declarations are atoms there too, so one generic checker
guards every write against the standing rows. A third-party kind is the same
machinery: declare its vocabulary and its shape, and from that moment the same
checker guards it.

Which is why this file has no special introspection door in it. The reflection
space is a space, so reading it is `space[pattern]` and extending it is
`space += row`, exactly as for any other knowledge, and that IS the example's
point made in Python.

`&rows` appears inside a declaration as the context the freshness claim is
about, so it is written as the name of a handle rather than as a bare symbol:
`m.space("&rows")` is where that name comes from.
"""

from petta import REFLECTION_SPACE, S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3576 to 1198, -2378 (-66.5%), by the twin contract
#: change: five `(test (match &petta ...) ...)` terms became five Python
#: `assert`s over the subscript door, so `test` left the engine five times
#: while the five matches it wrapped stayed in it, along with the four
#: declaration writes. Against the example's 13408 the ratio is 0.0893.
#: Prior: 3576, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1198


def twin(m):
    """Read four shipped catalog rows, then declare a kind of your own."""
    reflection = m.space(REFLECTION_SPACE)

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
    rows = m.space("&rows")
    reflection += (S.vocabulary, S["freshness-level"], S.live, S.cached, S.stale)
    reflection += (
        S.kind,
        S.freshness,
        S.symbol,
        S.pattern,
        S["one-of"](S["freshness-level"]),
    )
    reflection += (S.freshness, S[rows.space_name], S.edge(V.a, V.b), S.cached)

    assert [
        row.level
        for row in reflection[S.freshness(S[rows.space_name], V.shape, V.level)]
    ] == [S.cached]

    # (routed-by-shape head) gives the kind the SAME router the shipped
    # handles declarations use, inherited rather than reimplemented.
    reflection += (S["routed-by-shape"], S.freshness)
    assert S["routed-by-shape"](S.freshness) in reflection
