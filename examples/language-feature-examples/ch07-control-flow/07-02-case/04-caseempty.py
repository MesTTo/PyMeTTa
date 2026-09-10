"""Purpose: mirror the no-answer branch in examples/ch07-control-flow/07-02-case/04-caseempty.metta.

`Empty` selects a subject with no answers. In `wu`, `empty()` answers nothing,
so the `Empty` case returns 42. In `wu2`, `f()` answers 42 and the ordinary
case returns `ok`. Neither case treats the expression `()` as no answers.
Both definitions use Python `match`; the compiler keeps the `Empty` branch
outside the binding that would otherwise prune an unanswered subject.
[tested: test_empty_match_subject_selects_only_the_empty_branch;
commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
"""

from metta import S


def twin(m):
    """Take the `Empty` branch, then take an ordinary one instead."""
    @m.define
    def wu():
        match S.empty():
            case 1:
                return 2
            case S.Empty:
                return 42

    @m.define
    def f():
        # (= (f) 42)
        return 42

    @m.define
    def wu2():
        # (= (wu2) (case (f) ((42 ok) (Empty nok))))
        match f():
            case 42:
                return S.ok
            case S.Empty:
                return S.nok

    # !(test (wu) 42)
    assert wu() == [42]
    # !(test (wu2) ok)
    assert wu2() == [S.ok]


#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 8263 to 8301, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 8301 to 8314, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 8314 to 8248, on the release tree:
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
#: RE-PINNED 2026-08-25, 8248 to 8258, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 8258 to 8315 (+57), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 8315 to 8335 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 8335 to 5644 (-2691), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 5644 to 5631 (-13), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-02, 5631 to 5744 (+113), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 5744 to 5728 (-16), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 5728 to 5742 (+14), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-05, 5742 to 5269: both definitions now compile
#: Python match into the source's direct ordered case table, preserving Empty.
#: [measured: 5269, 5269, 5269 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch07-control-flow/07-02-case/04-caseempty.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 5269 to 5317 (+48), the one pricing pass at the 0.8.0
#: release cut, and trunk's own movement rather than any mechanism in this
#: twin: each pin was taken on the base its own branch had, and the September
#: merge wave has moved the engine's clause layout, the evaluation path and the
#: library's write doors since [measured 2026-09-06: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 5317 to 5475 (+158), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 5475 to 5523 (+48), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 5523 to 5435 (-88), metta_substitute_self/3 probes the
#: term for the text &self before walking it, one C write and one C substring
#: probe, where the twins-lane merge's one-equation door (08f6f4df) walked
#: every natively added equation in a named space unconditionally, so every
#: twin that adds or defines an equation in a named space drops by about that
#: equation's size in inferences; the same probe now guards the reader's per-
#: form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 5435 to 5429 (-6), the evaluation-fuel scope marker is
#: a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 5429 to 5455 (+26), boot content moved: the refusal
#: table and the typing point are modules this package did not have, three
#: convert doors became one, per-library faces are projections, and the engine
#: gained a catalog watch point, and SWI clause-indexing shape shifts a twin
#: count by tens whenever boot content moves, the mechanism every earlier entry
#: in these chains names. The watch point itself is one inference per &metta
#: write, which a twin that defines a function pays three of (2239 against 2236
#: on ch03 01-comments with the two announcement clauses taken out), and the
#: (limit ...) rows it exists for cost nothing at all: 2239 either way with
#: every row-backed bound removed, because boot seeds the mirror those bounds
#: are read from [measured 2026-09-08: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-PINNED 2026-09-08, 5429 to 5444 (+15), The engine and library predicates
#: now resolve through their owning modules and the explicit engine facade;
#: compiled program lookup crosses the added metta_engine tier [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 5444 to 5454 (+10), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 5455 to 5510 (+55), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 5510 to 5492 (-18), the door table landed (feat/space-
#: as-a-projection-of-door-rows merged at 6471faa37, its reconciliation fixes
#: at 58bf75947): every Space door is a generated alias over its body, the
#: catalog publishes the door contracts at boot as typed atoms, and the seam's
#: listeners publish on every registration, so boot content and clause layout
#: moved, which shifts a twin count by tens; measured on the merged tree
#: [measured 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 5492 to 5537 (+45), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 5454 to 5739 (+285), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 5739 to 5679 (-60), Sharing the fast-image hexadecimal
#: validator changes the engine predicate layout. The identity twin moves below
#: its declared band while the seven engine work counters move only at boot;
#: the native add and read slopes remain unchanged. Token storage and source
#: ownership retain their earlier measured costs and answer bags [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 5679 to 5809 (+130), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 5454 to 5504 (+50), Compiled shipped typing decisions
#: and initial vocabulary facts remove repeated interpretation; indexed
#: vocabulary membership replaces member-list scans; catalog reference checks
#: now respect transaction-local erasure. Paired controls and cut counts are
#: recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 5504 to 5766 (+262), the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): boot publishes the initial vocabulary
#: types from a compiled payload through the tokenized funnel, a warm
#: membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, -43 against the trunk's own pin of 5809 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +305 is what landed
#: on the trunk between the cut f0d33dcad and da0e5755d, tokens as storage
#: above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 5766 to 5826 (+60), a library's Prolog half compiles
#: beside itself on its first import and loads from the artifact after
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
#: RE-PINNED 2026-09-09, 5826 to 5836 (+10), engine/qlf_boot.pl gained the
#: hermetic child that writes the engine's own artifact set and every library
#: half's (qlf_child/2, qlf_regenerate_aside/1, qlf_child_boot/0,
#: qlf_shell_words/2), so no process's flags, initialisation file or packs
#: shape an artifact the tree shares; the boot file's added predicates move the
#: first definition's warm-up by ten, the load-structure movement its header
#: records for any boot-content change, and the lane's authoring constant moves
#: with it (warmup 1482); a twin importing a half pays the claim's freshness
#: check besides; measured on this tree with the artifacts warm, against the
#: pins of f26de01fb [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=5f8a823d23fbed5c7395912a89ba32760e2df4b1].
#: RE-PINNED 2026-09-09, 5836 to 5823 (-13), Public add-atom calls
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
#: extensions/python/tools/twin_coverage.py --repin; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
BUDGET = 5823
