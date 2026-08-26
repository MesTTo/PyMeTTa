"""examples/libraries/memo_variant_nonground.metta in Python: keying on structure.

`shape-kind` answers `pair` for anything shaped like a Pair, whatever the
variable inside is called, so two non-ground calls that differ only in variable
name are one cache key.

The equation goes to the container door because its head carries a PATTERN,
`(shape-kind (Pair $x $y))`, where a decorated function's parameters are always
plain variables. A `match` statement in a compiled body does lower to the case
tower and would destructure the argument, but it stores a different program: a
head pattern that misses answers the call back as data, where a case tower with
no matching arm prunes the branch. That gap is the residue entry.

Both claims are the call door, `m.fn.shape_kind(S.Pair(V.a, 2))`. The argument
CARRIES a variable without the answer depending on it, and the call answers
`pair` either way, so the example's point survives: the two calls differ ONLY
in the variable's name.
"""

from metta import S, V, equation, lib

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 28557 to 28633, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 28633 to 28642, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 28642 to 28652, on the release tree:
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
#: RE-PINNED 2026-08-26, 28652 to 29574 (+922), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=WORKTREE].
BUDGET = 29574


def twin(m):
    """Ask the same shape twice, under two different variable names."""
    m += lib.memo

    m += equation(S.shape_kind(S.Pair(V.x, V.y))).to(S.pair)
    m.eval(S.memoize(m.fn.shape_kind))

    assert m.fn.shape_kind(S.Pair(V.a, 2)) == [S.pair]
    assert m.fn.shape_kind(S.Pair(V.b, 2)) == [S.pair]
