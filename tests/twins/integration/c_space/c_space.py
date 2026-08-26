"""examples/integration/c_space/c_space.metta in Python: a space whose atoms live in C.

`cstore.c` holds the atoms and `cstore.pl` puts four clauses on the
foreign-space seam, so `&cstore` is a space like any other and nothing above it
knows there is a C backend. That is exactly why this twin reads like the spaces
twins: the store is a handle named by an ATOM rather than by text, `store +=
atom` writes, `store[pattern]` matches, and `store -= atom` takes one unifying
occurrence away, which is what `remove-atom` means everywhere.
`check-space-provider` takes that handle too, as a grounded operand, so nothing
here names a space as a symbol.

The provider file is consulted through `m.register_prolog(path=)`, the Python
door for what the example spells `(let "cstore.pl" (consult_global) provider)`.

One thing does not dissolve. The concurrent-writer form is DECLINED:
`hyperpose` runs its branches on real threads and the completion schedule
moves the inference count, which the residue records against P14.14. The
conformance check DOES dissolve now: with `lib.conformance` imported,
`check-space-provider` is this space's own function and the store handle
is its grounded operand, the example's call exactly, so this
Prolog-clause, C-store provider is held to the same contract as a Python
object. The import-free universal door,
`metta.testing.check_space_provider` handed the same handle, runs the
same engine checker and is pinned by test_conformance.py.
"""

from pathlib import Path

from metta import G, S, V, lib

#: The three engine libraries the example opens, spelled with their real
#: underscores: `S.lib_file` would name `lib-file`, which the tree does not ship.
LIBRARIES = (lib["lib_import"], lib.file, lib.conformance)

#: The build artefact and the provider that loads it, as host paths for a
#: Python door.
CSTORE_SO = Path("examples/integration/c_space/cstore.so")
CSTORE_PL = Path("examples/integration/c_space/cstore.pl")

#: What a healthy provider reports about itself, in the engine's own prose:
#: the capability inventory, the match family, the declared source
#: discipline, the canary round trip through the provider's own C-backed
#: writes, the pushdown claim, and the plan split.
REPORT = [
    G("enumerate: declared, seam:foreign_atoms/2 has clauses"),
    G("add: declared, seam:foreign_add/2 has clauses"),
    G("remove: declared, seam:foreign_remove/3 has clauses"),
    G("clear: declared, seam:foreign_clear/1 has clauses"),
    G("match: over-approximation holds over 1 atoms and their pattern families"),
    G("source: repeated, two enumerations agree"),
    G("round trip: add then enumerate answers the atom, and remove takes it back"),
    G("pushdown: 0 of 1 patterns claimed exact, and are"),
    G("plan: not declared, so a conjunction takes the engine's split"),
]


def twin(m):
    """Write into C, read back out of it, and prove the provider."""
    # (import! &self (library <name>)) three times: the write door imports,
    # and the receiver is the target space.
    for library in LIBRARIES:
        m += library

    if not CSTORE_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=CSTORE_PL)
    # The creation door on the handle's OWN context: `m.metta` answers the
    # owning evaluation context, so the store is a sibling of `m` by
    # construction rather than by the accident of a process-wide runtime.
    store = m.metta.space(S.cstore)

    # Writes and reads cross into C; the engine keeps unification for itself.
    store += [(S.edge, S.a, S.b), (S.edge, S.a, S.c), (S.edge, S.b, S.c)]
    assert [row.x for row in store[S.edge(S.a, V.x)]] == [S.b, S.c]

    # Removal is multiset subtraction: two atoms match `(edge a $any)`, so
    # clearing them takes two removals rather than one.
    store -= S.edge(S.a, V.any)
    assert len(store[S.edge(V.x, V.y)]) == 2
    store -= S.edge(S.a, V.other)
    assert [(row.x, row.y) for row in store[S.edge(V.x, V.y)]] == [(S.b, S.c)]

    # Identical copies are where the reading matters most: the count walks down
    # one at a time rather than clearing to nothing.
    store += [(S.dup, 1)] * 3
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 2
    store -= S.dup(1)
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 0

    # Every declared capability has clauses behind it, match over-approximates
    # over the whole pattern family, the declared source discipline holds, a
    # canary round-trips through the provider's own writes, and no pushdown
    # claim overreaches. The call mirrors the example exactly: the kit is
    # imported here, so `check-space-provider` is this space's own function
    # and the store handle is its grounded operand. The same checker is
    # reachable with NO import through `metta.testing.check_space_provider`,
    # whose Space-handle dispatch test_conformance.py pins.
    [checked] = m.fn.check_space_provider(store)
    assert list(checked) == REPORT


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 99307 to 99945, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 99945 to 99958, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 99958 to 111369, on the release tree:
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
#: RE-PINNED 2026-08-26, 111369 to 113901 (+2532), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 113901
