"""Purpose: examples/spaces/catalog.metta in Python: the catalog describes its own kinds.

Every declaration the engine acts on is an atom in the reflection space, and
the SHAPES of those declarations are atoms there too, so one generic checker
guards every write against the standing rows. A third-party kind is the same
machinery: declare its vocabulary and its shape, and from that moment the same
checker guards it.

Which is why this file has no special introspection door in it. The reflection
space is a space, so reading it is `space[pattern]` and extending it is
`space += row`, exactly as for any other knowledge, and that IS the example's
point made in Python. `metta.reflection` is the handle itself, not a name.

`&rows` appears inside a declaration as the context the freshness claim is
about, and it appears there as the HANDLE: a space is an ordinary term operand,
so `metta.space(S.rows)` goes straight into the row it is the subject of.
"""

import metta
from metta import S, V
from metta.vocabularies import Fidelity, Semiring

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-24: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 791 to 796, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 796 to 761, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-25, 761 to 783, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 783 to 747 (-36), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 747 to 767 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=WORKTREE].
BUDGET = 767
def twin(m):  # noqa: ARG001  -- the catalog lives in the reflection space; the default handle stays untouched
    """Read four shipped catalog rows, then declare a kind of your own."""
    reflection = metta.reflection

    # The fidelity vocabulary is the four words the handles router acts on.
    assert [
        (row.a, row.b, row.c, row.d)
        for row in reflection[S.vocabulary(S.fidelity, V.a, V.b, V.c, V.d)]
    ] == [(
        S[Fidelity.Exact],
        S[Fidelity.Partial],
        S[Fidelity.Sound],
        S[Fidelity.Refuse],
    )]

    # The handles kind row is the shape every (handles ...) declaration fits.
    assert [
        row.claim for row in reflection[S.kind(S.handles, V.ctx, V.entry, V.claim, V.det)]
    ] == [S.one_of(S.fidelity)]

    # Orderedness is a claim on a semiring value, which is what (top k ...)
    # consults rather than a word list compiled into the engine. The claim
    # carries the DIRECTION beside the property, because ordered alone does
    # not say which end a top-k slice takes: ranked counts down from the
    # best, tropical counts up from the cheapest.
    assert [
        (row.p, row.direction)
        for row in reflection[
            S.claim(S.semiring, S[Semiring.ranked], V.p, V.direction)
        ]
    ] == [(S.ordered, S.descending)]
    assert [
        (row.p, row.direction)
        for row in reflection[
            S.claim(S.semiring, S[Semiring.tropical], V.p, V.direction)
        ]
    ] == [(S.ordered, S.ascending)]

    # A third-party kind is the same machinery: declare its vocabulary and its
    # shape, and the same checker guards it.
    rows = metta.space(S.rows)
    reflection += (S.vocabulary, S.freshness_level, S.live, S.cached, S.stale)
    reflection += (S.kind, S.freshness, S.symbol, S.pattern, S.one_of(S.freshness_level))
    reflection += (S.freshness, rows, S.edge(V.a, V.b), S.cached)

    assert [
        row.level for row in reflection[S.freshness(rows, V.shape, V.level)]
    ] == [S.cached]

    # (routed-by-shape head) gives the kind the SAME router the shipped
    # handles declarations use, inherited rather than reimplemented.
    reflection += (S.routed_by_shape, S.freshness)
    assert S.routed_by_shape(S.freshness) in reflection
