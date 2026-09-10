"""Purpose: examples/ch19-spaces-backed-by-anything/19-02-a-space-in-c/01-c_space.metta in Python: a space whose atoms live in C.

`cstore.c` holds the atoms and `cstore.pl` puts four clauses on the
foreign-space seam, so `&cstore` is a space like any other and nothing above it
knows there is a C backend. That is exactly why this twin reads like the spaces
twins: the store is a handle named by an ATOM rather than by text, `store +=
atom` writes, `store[pattern]` matches, `store -= atom` takes one unifying
occurrence away, and `del store[pattern]` drains every one, which is what
`remove-atom` means everywhere.
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
#: Resolved against the REPOSITORY rather than the caller's directory. As a
#: relative path this twin's whole body was skipped by any runner whose
#: working directory was not the repository root -- the pytest lane runs from
#: extensions/python -- so `if not CSTORE_SO.exists(): return` fired and the
#: file certified nothing while reporting green [measured 2026-09-01].
_REPO = Path(__file__).resolve().parents[6]
CSTORE_SO = _REPO / Path("examples/ch19-spaces-backed-by-anything/19-02-a-space-in-c/cstore.so")
CSTORE_PL = _REPO / Path("examples/ch19-spaces-backed-by-anything/19-02-a-space-in-c/cstore.pl")

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

    # `del` is the DRAIN, what (remove-atom &cstore (edge a $any)) means:
    # every atom that unifies goes, so both edges from a leave together and
    # the one that does not start at a stays. The provider's own door is
    # finer and stays so -- seam:foreign_remove/3 takes one occurrence and
    # reports it -- so this is one MeTTa call and two C calls.
    del store[S.edge(S.a, V.any)]
    assert [(row.x, row.y) for row in store[S.edge(V.x, V.y)]] == [(S.b, S.c)]

    # Identical copies are where the two grains separate. `-=` and remove()
    # are the C provider's own grain, one occurrence per call, so the count
    # walks down one at a time; `del` takes what is left in one crossing.
    store += [(S.dup, 1)] * 3
    assert store.remove(S.dup(1)) is True
    assert len(store[S.dup(V.n)]) == 2
    store -= S.dup(1)
    assert len(store[S.dup(V.n)]) == 1
    del store[S.dup(V.n)]
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
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
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
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 113901 to 115008 (+1107), one corpus pricing pass on
#: the merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 115008 to 115167 (+159), the -= drain law reaching the
#: C-store pair: the twin healed to the two grains, remove() one occurrence and
#: -= draining, mirroring the metta side [measured 2026-09-01: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 115167 to 115205 (+38), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 115205 to 114999 (-206), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 114999 to 115287 (+288), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 115287 to 115302 (+15), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 115302 to 134843 (+19541), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 134843 to 139026 (+4183), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 139026 to 139094 (+68), the merges between this lane's
#: burn-down base (dfd5003f) and the tree that merged it, placed by a first-
#: parent ladder through the lane's own driver over ten twins at f8c4b672,
#: 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
#: tmp/integrator-849a9e/mergeTW-twin-ladder.log): the catalog-types merge
#: (1a3579fa) moves every twin by a lookup-and-layout step of about +5 for a
#: twin that makes no typed call and about +35 for one that does, plus about +6
#: per compiled definition through the argument-delivery check at the write
#: (the authoring fit re-measured 1370+1307 to 1406+1309), and +1411 for the
#: catalog twin that enumerates the 280 new rows; the two-sided-fragments merge
#: (4af59757) moves the sequence-variable twins by what their fixed rows now
#: compute (+2604 for the two-sided fragments, -217 for the fence, +19 for
#: restricted spaces); the every-atom merge (90c08119) re-authored the reading-
#: forms twin into the sread half (+3017) and added forty-six twins pinned on
#: its own base 31d54e19, which the merges since moved by the same clusters;
#: the gate-hygiene merge (ad762ee7) makes the tabling twins cheaper by the wfs
#: library no longer loading eagerly. Every twin here re-reads its budget on
#: the merged tree, minimum of three fresh processes [measured 2026-09-08: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-PINNED 2026-09-08, 139094 to 139080 (-14), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 139080 to 148881 (+9801), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 148881 to 149190 (+309), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 149190 to 149315 (+125), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 149315 to 149483 (+168), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 149315 to 150705 (+1390), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 150705 to 150873 (+168), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 149315 to 138740 (-10575), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 138740 to 149298 (+10558), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 149298 to 150856 (+1558), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -17 against the trunk's own pin of 150873 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +1575 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 150856 to 40926 (-109930), a library's Prolog half
#: compiles beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-PINNED 2026-09-09, 40926 to 40920 (-6), Public add-atom calls
#: metta_add_atom/4 directly and the native bulk loop calls add_sexp_in/5
#: directly, removing one forwarding inference per accepted atom while keeping
#: the atomic token clock, hooks and errors. Open native enumeration uses the
#: shared native_storage_functor/2 mapping, including parametric scalar
#: storage. Receipt scopes retain the nearest unnested transaction and post no
#: cleanup when no reservation exists. Full-lane ten-round observations on the
#: repaired tree place this point below the published budget; the provisioned
#: cut is 3e5855a35d7b206c847845f12467551ea4c54a59. See the 2026-09-09 entries in
#: docs/journal/2026-09-07-every-fact-has-a-token.md. Autoload-only excursions
#: are excluded from this point selection and keep their pins [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 40920
