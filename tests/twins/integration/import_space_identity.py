"""examples/integration/import_space_identity.metta in Python: one identity per space.

Two spaces import the same file. Each gets its own copy of what the file
defines, exactly once, and the space that did the importing gets nothing: in
its own space the imported name stays data, an unreduced term answering itself.

`(bind! &import-space-a (new-space))` is `metta.space(name)` plus a Python name
binding, which is what a token was for, and the name is an ATOM rather than
text: `metta.space` takes one, and the ampersand belongs to the door rather
than to the author. Everything the claims ask goes through the handle:
`space[pattern]` matches it and `space.eval(term)` evaluates in it, which is
what the example spells `(metta term %Undefined% &space)`.
"""

from metta import S, lib

#: The file both spaces import, from the repository root: a Python program has
#: no importing file to resolve a relative import against.
PAYLOAD = S["examples/integration/_fixtures/imports/overhaul/space_payload"]

#: What the payload puts in an importing space, and what it defines there.
MARKER = S.import_space_marker()
FUNCTION = S.import_space_function()

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5383 to 5526, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 5526 to 5527, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 5527 to 5539, on the release tree:
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
#: RE-PINNED 2026-08-26, 5539 to 5449 (-90), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 5449


def twin(m):
    """Import one payload into two spaces, and ask all three what they hold."""
    # The creation door on the handle's OWN context: `m.metta` answers the
    # owning evaluation context, so both spaces are siblings of `m` by
    # construction rather than by the accident of a process-wide runtime.
    a = m.metta.space(S.import_space_a)     # (bind! &import-space-a (new-space))
    b = m.metta.space(S.import_space_b)     # (bind! &import-space-b (new-space))

    # (import! &a payload) and (import! &b payload): the RECEIVER of the
    # write door is the target space, so each space imports its own copy.
    for space in (a, b):
        space += lib(PAYLOAD)

    # Each importing space holds the marker, once.
    assert len(a[MARKER]) == 1
    assert len(b[MARKER]) == 1

    # And each ran its own copy of the definition, once.
    assert a.eval(FUNCTION) == [S.one_result]   # (metta (import-space-function) %Undefined% &import-space-a)
    assert b.eval(FUNCTION) == [S.one_result]

    # The caller imported nothing, so here the name is still data.
    assert m.eval(FUNCTION) == [FUNCTION]
