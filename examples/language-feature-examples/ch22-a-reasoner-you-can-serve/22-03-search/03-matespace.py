"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-03-search/03-matespace.metta in Python: a space grown to a million atoms.

`expand` doubles every `num` atom into an M-branch and a W-branch, `expandK`
does that 390 times, `mate` pairs the branches, and the whole thing answers
just over a million atoms. It is a scale example, and the scale is what its
Python twin has to respect.

The final count stays inside the engine:
`m.answers(call, under=counting).one()` maps every answer derivation to one
and returns one TaggedAnswer whose annotation is 1,063,919, rather than
materializing that million atoms in Python [tested:
tools/twin_coverage.py --measure --rounds 1 examples/ch22-a-reasoner-you-can-serve/22-03-search/03-matespace.metta;
commit=2e627a593413191cda3170f2eb716835f7f62543].

The three definitions whose bodies name `case` or `once` remain terms because
neither translator form is in the function registry (residue, P14.4).
`expandK` and the driver compile: their sequencing is assignment, the driver's
ambient handle comes from `context-space`, and its seed write is `space +=`.
"""

from metta import S, V, counting, equation, fn, if_, match


def twin(m):
    """Grow a space by 390 doublings, mate the branches, and count what is left."""
    nodup = S.add_atom_no_duplicate

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    seen = S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
    m += equation(nodup(V.space, V.atom)).to(
        if_(S.eq((), seen), S.add_atom(V.space, V.atom), S.empty())
    )

    # (= (expand) (case (match &self (num $t) $t) (($t ((add-atom-no-duplicate ...))))))
    m += equation(S.expand()).to(
        S.case(
            S.match(m, S.num(V.t), V.t),
            ((V.t, (nodup(m, S.num(S.M(V.t))), nodup(m, S.num(S.W(V.t))))),),
        )
    )

    # (= (mate) (case (match &self (num (M $t)) $t) (($t (case (once ...) ...)))))
    paired = S.case(
        S.once(S.match(m, S.num(S.W(V.t)), V.t)),
        ((V.t, nodup(m, S.num(S.C(V.t)))),),
    )
    m += equation(S.mate()).to(S.case(S.match(m, S.num(S.M(V.t)), V.t), ((V.t, paired),)))

    # (= (expandK $n) (if (== $n 0) done (let $temp1 (expand) (expandK (- $n 1)))))
    @m.define(name="expandK")  # camelCase is outside the underscore map
    def expand_k(n: int):
        if fn.eq(n, 0):  # engine equality is intentional
            return S.done
        _step = fn.expand()
        return expand_k(n - 1)

    # (= (mate-space-demo $K) (let* (($s (add-atom ...)) ($g (expandK $K)) ($h (mate)))
    #                               (match &self (num $1) (num $1))))
    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _grown = fn.expandK(k)
        _mated = fn.mate()
        return match(space, S.num(V.x), S.num(V.x))

    assert (
        m.answers(S.mate_space_demo(390), under=counting).one().annotation == 1063919
    )


#: Why this twin sits below the top rung, stated once for the whole file.
RUNG = (
    "expand, mate and add-atom-no-duplicate are built as terms: their bodies "
    "name case or once, neither of which a compiled body reaches (residue, P14.4)"
)

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 32666765 to 32666788, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 32666788 to 32666790, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 32666790 to 32666761, on the release tree:
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
#: RE-PINNED 2026-08-25, 32666761 to 32666766, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 32666766 to 32666757: the final million-answer
#: observation now uses answers(..., under=counting) and crosses one scalar
#: [measured: 32666757 inferences;
#: command=python extensions/python/tools/twin_coverage.py;
#: fixture=full-lane 390 doublings and 1063919 answers; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
#: RE-PINNED 2026-08-26, 32666757 to 116492891 (+83826134): 6917bef7 made encoded
#: generator tuple yields cross as relational candidate rows the engine
#: unifies per row, where they had been direct emissions; this twin's
#: move generators pay it on every yielded move. Measured at the exact
#: pair: 32,666,762 at a58e3d17 and 116,491,178 at 6917bef7. The answers
#: are unchanged; ai-brief-p14-relational-ops-fastpath carries the
#: ground-direction fast path [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 116492891 to 116492911 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-08-26, 116492911 to 116491412 (-1499), by the
#: specializer argument-walk fix. Planning a specialization grafts a call argument onto the
#: equation's head pattern one position at a time, and that walk
#: metacalled a yall lambda per position, so each fresh process paid
#: '>>'/4's one-time resolution wherever its first binding plan landed
#: and 13 further inferences at every later position. The walk is
#: first-order now, at 4.0 inferences per position against 17.0.
#: [measured: two independent full-lane rounds on this tree agreeing exactly, against one on the unchanged tree and one on the same tree plus an inert never-called clause; command=python extensions/python/tools/twin_coverage.py; fixture=p14-specializer-tax off 694c12f7 with engine/reader.so and the MORK backend; commit=7e7cac85fee08c117032b2efa5a58a40f3b21365].
#: RE-PINNED 2026-08-26, 116492911 to 32668415 (-83824496, -71.9%), which
#: returns this twin to its pre-6917bef7 cost: `answers(..., under=counting)`
#: builds a view whose ONLY source is the scalar, so the count is that view's
#: whole evaluation and the repeatability question cannot arise. Asking it
#: anyway sent this effect-bearing goal through a materializing pass that
#: encoded and crossed all 1,063,919 answers to reach a number nobody kept
#: [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-relational-fastpath off 694c12f7 with engine/reader.so and the MORK artefact; commit=00a30179a1acd55aa969b44a977fb9a38e2e2df2].
#: RE-PINNED 2026-08-26, at the relational-counting merge: 32666910.
#: Both parents re-pinned this budget and neither number survives the
#: merge, so it is re-measured here rather than resolved to a side.
#: The two mechanisms above COMPOSE, and the world-admission merge's
#: admission guard lands on top of them: this lineage read 116491412,
#: the counting branch read 32668415 against its own base, and the
#: merged tree reads 32666910
#: [measured: min-of-3 serial fresh processes on the resolved merge
#: tree; command=python extensions/python/tools/twin_coverage.py
#: --measure --rounds 3 ../../examples/<this example>;
#: fixture=engine/reader.so and the MORK artefact present;
#: commit=58d0332489da668251edcd52ccc5cb42ba2e57bb].
#: RE-PINNED 2026-09-01, 32666910 to 24100901 (-8566009), one corpus pricing
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
#: RE-PINNED 2026-09-01, 24100901 to 24100876 (-25), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 24100876 to 24100883 (+7), generic Python operators
#: now dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 24100883 to 24103097 (+2214), exact numeric
#: annotations retain native operator heads, publish MeTTa type declarations,
#: and leave relational heads only where static proof is unavailable [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 24103097 to 24103374 (+277), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 24103374 to 24103388 (+14), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 24103388 to 24103414 (+26), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 24103414 to 24102512 (-902), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 24102512 to 24107867 (+5355), trunk's own movement
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
#: RE-PINNED 2026-09-08, 24107867 to 24107907 (+40), the merges between this
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
#: RE-PINNED 2026-09-08, 24107907 to 24107404 (-503), metta_substitute_self/3
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
#: RE-PINNED 2026-09-08, 24107404 to 24107425 (+21), boot content moved: the
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
#: RE-PINNED 2026-09-08, 24107404 to 24107778 (+374), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 24107778 to 24107788 (+10), The engine and library
#: module boundaries retain explicit lookup owners, including host registration
#: and returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 24107788 to 24106792 (-996), the module boundary
#: merged with trunk's later packages (refactor/engine-and-libraries-as-modules
#: at b64291369): every space now resolves through one more chain link, prelude
#: -> metta_engine -> user, the engine's measured export list is imported into
#: the host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 24107425 to 24106514 (-911), The typed host door
#: catalog is published before user code. Its declarations change catalog
#: lookup indexes; generated public names bind directly to their existing
#: bodies [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 24106514 to 24106830 (+316), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 24106830 to 24106840 (+10), structured concurrency
#: landed (feat/structured-concurrency merged at f80cc416d): every space mint
#: records its allocation in the library's lifetime rows, every write and run
#: pays the ownership hook and every drop asks the library whether a scope owns
#: the name, measured on a pristine control as 32 per mint, 2 per write and 44
#: per drop with none per read; measured on the merged tree [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 24106792 to 24121213 (+14421), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 24121213 to 24121153 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 24121153 to 24121246 (+93), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 24106792 to 24106825 (+33), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 24106825 to 24107109 (+284), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 24107109 to 24121468 (+14359), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, +222 against the trunk's own pin of 24121246 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +14137 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 24121468 to 24121528 (+60), a library's Prolog half
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
#: RE-PINNED 2026-09-09, 24121528 to 24121538 (+10), engine/qlf_boot.pl gained
#: the hermetic child that writes the engine's own artifact set and every
#: library half's (qlf_child/2, qlf_regenerate_aside/1, qlf_child_boot/0,
#: qlf_shell_words/2), so no process's flags, initialisation file or packs
#: shape an artifact the tree shares; the boot file's added predicates move the
#: first definition's warm-up by ten, the load-structure movement its header
#: records for any boot-content change, and the lane's authoring constant moves
#: with it (warmup 1482); a twin importing a half pays the claim's freshness
#: check besides; measured on this tree with the artifacts warm, against the
#: pins of f26de01fb [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=5f8a823d23fbed5c7395912a89ba32760e2df4b1].
#: RE-PINNED 2026-09-10, 24121538 to 24119985 (-1553), the binding resolves
#: Janus maplist/2 at boot, removing its first-failure autoload; one compiled
#: option policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-10, 24119985 to 24119980 (-5), the bounds frame watcher
#: now transfers its watch to the nearest live transaction, preventing
#: notification of an engine's discarded outer query frame. The changed boot
#: predicate set also changes current_predicate/1's catalog-arity enumeration
#: order. A same-worktree old/current/restore control and native call-site
#: coverage locate each five-inference step in spaces:metta_catalog_clause/2:
#: current_predicate, the arity guard, functor, metta_storage_term and clause.
#: No workload or lookup implementation changes. See
#: docs/journal/2026-09-09-the-binding-collapse.md. These are three fresh
#: sequential samples per row with 32 concurrent row runners and
#: file_search_cache_time=9223372036854775807 before boot. The point allowance
#: and every empirical envelope are unchanged [measured 2026-09-10: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 24119980

#: OVERRUN 2026-09-07, 1434400: it names `expand` and `expandK` as definitions
#: and asserts the atom count, where the example writes them as equations.
#: Measured 24107867 against a ceiling of 22673518; a minimal twin of this
#: example costs 19846949, inside the ceiling's 22673518, so the distance is
#: this twin's own program [measured 2026-09-07: one fresh process per side;
#: command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
OVERRUN = 1434400

#: DIVERGED 2026-09-07, the example holds 4 atoms the twin does not (4 =) and
#: the twin holds 5 the example does not (1 :, 4 =): the twin is an ordinary
#: Python program and its body lowers to the engine's own forms: a match
#: statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "f11cab2a09098d5a4a2150749e1dab72a3ddaa8d4a1aee0bee2b5203e7e1cac7"
