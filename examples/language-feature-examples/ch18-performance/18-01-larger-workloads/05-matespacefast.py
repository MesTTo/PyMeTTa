"""Purpose: examples/ch18-performance/18-01-larger-workloads/05-matespacefast.metta in Python: a million and a half atoms.

`rewriteK` writes three atoms per level and recurses down two branches, so
nineteen levels leave 1,572,862 atoms in the space; `mate-space-demo` runs that
and then matches everything back out. The claim is how many came back.

The recursive equation compiles and then cannot run, which is why it is built
here. A compiled `if` wraps its condition in `py-truthy` and `==` lowers to
`py-eq`, so every level spends reductions the original does not, and the evaluator's
default 100,000 stack bound is reached long before nineteen levels: the
compiled pair answers `(Error (rewriteK (M (W ...)) 2) StackOverflow)` at K=14
where the built pair completes K=19 [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
`m.limits` bounds inferences and time and not stack depth, and the example
states no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone. Residue P14.4 and P14.14.

The count IS Python's, and it is the most expensive line in this folder.
`len(answers)` is what `(length (collapse X))` dissolves into, and here the
answers are 1,572,862 atoms: 295,442,370 inferences, 66 seconds and 5.3 GB of
resident memory in one process, against the engine's own count which never
materialises one [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. It no longer FAILS,
which it did when this twin was first written: the answer view streams where
the old door built one Prolog list, so the wall moved from "cannot run" to
"expensive". The missing door is the one peanofast.py names, a query that
projects or aggregates before it crosses (residue, P14.7); the cost of not
having it is the library's.

The space every equation writes into and matches is the HANDLE, because a space
is an ordinary term operand.
"""

from metta import S, V, equation, fn, if_, match


def twin(m):
    """Rewrite nineteen levels deep, then count what landed."""
    m += equation(S.rewriteK(V.t, V.n)).to(
        if_(V.n.eq(0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V["_1"], S.add_atom(m, S.num(S.M(V.t)))),  # rung: as above
                           (V["_2"], S.add_atom(m, S.num(S.W(V.t)))),  # rung: as above
                           (V["_3"], S.add_atom(m, S.num(S.C(V.t))))),  # rung: as above
                          (S.rewriteK(S.M(V.t), V.n - 1),
                           S.rewriteK(S.W(V.t), V.n - 1)))))

    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _rewritten = fn.rewriteK(S.Z, k)
        return match(space, S.num(V.stored), S.num(V.stored))

    assert len(m.fn.mate_space_demo(19)) == 1572862


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 68713127 to 68713120, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 68713120 to 68713144, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 68713144 to 68713105, on the release tree:
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
#: RE-PINNED 2026-08-25, 68713105 to 68713114, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 68713114 to 324566150 (+255853036): 6917bef7 made encoded
#: generator tuple yields cross as relational candidate rows the engine
#: unifies per row, where they had been direct emissions; this twin's
#: move generators pay it on every yielded move. Measured at the exact
#: pair: 32,666,762 at a58e3d17 and 116,491,178 at 6917bef7. The answers
#: are unchanged; ai-brief-p14-relational-ops-fastpath carries the
#: ground-direction fast path [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 324566150 to 324566172 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 324566172 to 74483636 (-250082536, -77.1%), the
#: largest of the family because it is the answer-heaviest: `len(...)` on an
#: effect-bearing goal had to encode and cross all 1,572,862 answers to reach
#: one number. The count and the values now come from ONE evaluation that
#: holds its answers unencoded in the engine. Crossing an answer costs
#: 9.1 + 8.0 per term node in engine inferences, measured over a depth sweep,
#: and that whole product is what a discarded length used to pay
#: [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-relational-fastpath off 694c12f7 with engine/reader.so and the MORK artefact; commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
#: RE-PINNED 2026-09-01, 74483636 to 74207335 (-276301), one corpus pricing
#: pass on the merged tree for the 2026-08-27..09-01 engine span
#: (8e75816d..f0744f86), whose four mechanisms are decomposed per lane in
#: benchmarks/baseline.json and ai-parametricity-audit.md passes 10-16: the
#: seam-offer routing and its one-wrap fold (net +8 inferences per evaluation),
#: the strict-scope removal leaving the eval path, the doubling cursor chunk
#: (~3 engine-side inferences per answer replacing per-answer crossings; drains
#: halve on CPU), and the aligned-path work; thirteen twins additionally carry
#: the idiom sweep's local deltas tabulated in the twin-idioms notes, none
#: above 347 [measured 2026-09-01: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 74207335 to 74207322 (-13), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-02, 74207322 to 74207402 (+80), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 74207402 to 74207390 (-12), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 74207390 to 74207404 (+14), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 74207404 to 74201576 (-5828), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 74201576 to 74988457 (+786881), trunk's own movement
#: since each twin's pin was taken on the base its own branch had: twenty-two
#: first-parent steps between the 0.8.0 release re-pin and this tree, the
#: prelude's move into Prolog the largest of them at +39 to +115 a twin and
#: -65,806 on the error algebra, the live-views merge -45 on every twin that
#: writes, the catalog and get-type repairs +169 on the types chapter, and the
#: rest SWI clause-indexing layout as the boot image grew; this tree also
#: stores the compiled default space operand as &self rather than a (context-
#: space) call [measured 2026-09-07: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 74988457 to 74988495 (+38), the merges between this
#: lane's burn-down base (dfd5003f) and the tree that merged it, placed by a
#: first-parent ladder through the lane's own driver over ten twins at
#: f8c4b672, 4af59757, 90c08119, ad762ee7, 72f9cdf2 and 249389cb (ai-
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
#: RE-PINNED 2026-09-08, 74988495 to 74988185 (-310), metta_substitute_self/3
#: probes the term for the text &self before walking it, one C write and one C
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
#: RE-PINNED 2026-09-08, 74988185 to 74988201 (+16), boot content moved: the
#: refusal table and the typing point are modules this package did not have,
#: three convert doors became one, per-library faces are projections, and the
#: engine gained a catalog watch point, and SWI clause-indexing shape shifts a
#: twin count by tens whenever boot content moves, the mechanism every earlier
#: entry in these chains names. The watch point itself is one inference per
#: &metta write, which a twin that defines a function pays three of (2239
#: against 2236 on ch03 01-comments with the two announcement clauses taken
#: out), and the (limit ...) rows it exists for cost nothing at all: 2239
#: either way with every row-backed bound removed, because boot seeds the
#: mirror those bounds are read from [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 74988185 to 74988245 (+60), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 74988245 to 74988255 (+10), The engine and library
#: module boundaries retain explicit lookup owners, including host registration
#: and returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
BUDGET = 74988255

#: DIVERGED 2026-09-07, the example holds 1572864 atoms and the twin 1572864,
#: over the 50000 this lane enumerates, so the difference is pinned as the two
#: digests: trunk's own movement since each twin's pin was taken on the base
#: its own branch had: twenty-two first-parent steps between the 0.8.0 release
#: re-pin and this tree, the prelude's move into Prolog the largest of them at
#: +39 to +115 a twin and -65,806 on the error algebra, the live-views merge
#: -45 on every twin that writes, the catalog and get-type repairs +169 on the
#: types chapter, and the rest SWI clause-indexing layout as the boot image
#: grew; this tree also stores the compiled default space operand as &self
#: rather than a (context-space) call [measured 2026-09-07: the two stored-atom
#: surpluses, one fresh process per side; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "0b995b079c8509570d648f5387f6ba4787cc0739d4769a757e2b79974aed0179"

#: OVERRUN 2026-09-08, 2900000: the count is Python's. `len(answers)` is what
#: `(length (collapse X))` dissolves into and the answers here are 1,572,862
#: atoms, so this twin MATERIALISES what the engine's own count never does; the
#: door that would project or aggregate before crossing is residue P14.7, and
#: until it exists the cost of not having it is the library's. Measured
#: 74,988,457 against a ceiling of 72,106,898; a MINIMAL twin of this example
#: -- its own forms stored and asked through the structured door, nothing else
#: -- costs 62,402,666, inside that ceiling, so the distance is this twin's own
#: program [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
OVERRUN = 2900000
