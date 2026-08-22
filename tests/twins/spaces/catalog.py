"""The Python twin of examples/spaces/catalog.metta: the catalog describes its own kinds.

Every declaration the engine acts on is an atom in the reflection space, and the
SHAPES of those declarations are atoms there too, so one generic checker guards
every write against the standing rows and a third-party kind is the same
machinery: declare its vocabulary and its shape, and the checker guards it from
that moment.

The reflection space is a space like any other, so it is a handle here and its
four declarations go in through `reflection += row`. That is the point the
example makes about itself, made in Python: library introspection is ordinary
matching and library extension is ordinary writing.
"""

from petta import REFLECTION_SPACE, S, V, expr

#: The answer group a write form contributes: `add-atom` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4820 to 3576, -1244 (-25.8%), by the P14 twin-style
#: rewrite, and the whole delta is the four declarations: each moved from
#: evaluating an (add-atom &petta ...) term to `reflection += row`, 311 a write,
#: the top of the 239-to-311 band this folder measures across six files for a
#: plain-atom write. The five assertions are the same terms spelled with named
#: symbols and tuples.
#: Prior: ADDED 2026-08-22 at 4820 by the wave-3 spaces baseline.
BUDGET = 3576


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    reflection = m.space(REFLECTION_SPACE)
    here = S[reflection.space_name]

    # The shipped rows are ordinary data: the fidelity vocabulary is the four
    # words the handles router acts on.
    # !(test (match &petta (vocabulary fidelity $a $b $c $d) ($a $b $c $d))
    #        (Exact Partial Sound Refuse))
    yield m.eval(
        S.test(
            S.match(
                here,
                S.vocabulary(S.fidelity, V.a, V.b, V.c, V.d),
                (V.a, V.b, V.c, V.d),
            ),
            (S.Exact, S.Partial, S.Sound, S.Refuse),
        )
    )

    # The handles kind row is the shape every (handles ...) declaration must fit.
    # !(test (match &petta (kind handles $ctx $entry $claim $det) $claim)
    #        (one-of fidelity))
    yield m.eval(
        S.test(
            S.match(
                here,
                S.kind(S.handles, V.ctx, V.entry, V.claim, V.det),
                V.claim,
            ),
            S["one-of"](S.fidelity),
        )
    )

    # Orderedness is a claim on a semiring value rather than a word list
    # compiled into the engine.
    # !(test (match &petta (claim semiring ranked $p) $p) ordered)
    yield m.eval(
        S.test(
            S.match(here, S.claim(S.semiring, S.ranked, V.p), V.p),
            S.ordered,
        )
    )

    # A third-party kind is the same machinery: declare its vocabulary and its
    # shape, and the same checker guards it.
    # !(add-atom &petta (vocabulary freshness-level live cached stale))
    reflection += (S.vocabulary, S["freshness-level"], S.live, S.cached, S.stale)
    yield WROTE
    # !(add-atom &petta (kind freshness symbol pattern (one-of freshness-level)))
    reflection += (
        S.kind,
        S.freshness,
        S.symbol,
        S.pattern,
        S["one-of"](S["freshness-level"]),
    )
    yield WROTE
    # !(add-atom &petta (freshness &rows (edge $a $b) cached))
    reflection += (S.freshness, S["&rows"], S.edge(V.a, V.b), S.cached)
    yield WROTE

    # !(test (match &petta (freshness &rows $shape $level) $level) cached)
    yield m.eval(
        S.test(
            S.match(
                here,
                S.freshness(S["&rows"], V.shape, V.level),
                V.level,
            ),
            S.cached,
        )
    )

    # (routed-by-shape head) gives the kind the SAME router the shipped handles
    # declarations use, inherited rather than reimplemented.
    # !(add-atom &petta (routed-by-shape freshness))
    reflection += (S["routed-by-shape"], S.freshness)
    yield WROTE

    # !(test (match &petta (routed-by-shape freshness) found) found)
    yield m.eval(
        S.test(
            S.match(here, S["routed-by-shape"](S.freshness), S.found),
            S.found,
        )
    )
