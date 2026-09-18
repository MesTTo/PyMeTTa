"""Purpose: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/06-git_import.metta in Python: a repository as a library.

Four acts, then one question. A fixture Prolog file answers a clone URL,
`git-import!` clones that repository into `./repos`, the clone is imported as
an ordinary named library, and the function it ships answers.

The Prolog step is Python's own door: `m.register_prolog(path=, names=)` is
what `import_prolog_functions_from_file` names in MeTTa, and it takes the file
and the predicates to export in the same order. The two imports take the
write door with the receiver as the target space, and the clone's entry
point is the dotted part, `FIXTURE_LIB.fixture`, the two-argument
`(library alias inner)` form. `git-import!` stays the engine's own
function: cloning is packaging, and packaging's Python spelling is pip.

Two library names take lib's bracket door: `lib_import` strips to the
keyword `import`, which Python cannot say after a dot, and
`metta_fixture_lib` sits outside the `lib_` family the attribute map
prefixes. `git_fixture_url` keeps fn's bracket for the same reason it
always did: its underscores are real and the function map writes hyphens.
"""

from pathlib import Path

from metta import S, lib

#: The directory `git-import!` clones into, and the fixture's own Prolog file.
#: Both are paths, so both are `pathlib.Path`: a path is never text, at the
#: call door or at the Python one.
REPOS = Path("./repos")
FIXTURE_PL = Path("examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/git_fixture.pl")

#: The library shipped with the engine, the Prolog predicate the fixture
#: exports, and the library the clone provides. Every one carries a genuine
#: underscore, so every one takes rung 5.
LIB_IMPORT = lib["lib_import"]
FIXTURE_URL = S["git_fixture_url"]
FIXTURE_LIB = lib["metta_fixture_lib"]


def twin(m):
    """Build a repository, clone it, import it, ask it a question."""
    # (import! &self (library lib_import)): the write door imports, and the
    # receiver is the target space.
    m += LIB_IMPORT

    # The URL comes from Prolog, which register_prolog installs as a MeTTa
    # function of one argument: the base directory in, the clone URL out.
    m.register_prolog(path=FIXTURE_PL, names=["git_fixture_url"])
    m.fn["git-import!"](FIXTURE_URL(REPOS))     # (git-import! (git_fixture_url "./repos"))

    # The clone is now an ordinary named library, and the dotted part is the
    # two-argument (library metta_fixture_lib fixture) form.
    m += FIXTURE_LIB.fixture

    assert m.fn.fixture_answer(14) == [42]   # [42]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 34545 to 34621, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 34621 to 34632, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 34632 to 34640, on the release tree:
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
#: RE-PINNED 2026-08-26, 34640 to 34108 (-532), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 34108 to 34342 (+234), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 34342 to 34334 (-8), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 34334 to 34353 (+19), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 34353 to 34531 (+178), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 34531 to 34701 (+170), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 34701 to 38598 (+3897), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-PINNED 2026-09-08, 38598 to 38593 (-5), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 38593 to 38581 (-12), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 38581 to 38573 (-8), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 38573 to 38583 (+10), boot content moved: the refusal
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
#: RE-PINNED 2026-09-08, 38573 to 37026 (-1547), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 37026 to 38510 (+1484), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 38510 to 38559 (+49), the module boundary merged with
#: trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 38583 to 37099 (-1484), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-08, 37099 to 38583 (+1484), The published host catalog
#: changes name lookup while the git fixture registers its Prolog entry and
#: imports the cloned library [measured 2026-09-08: min-of-3 serial fresh
#: commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 38583 to 38559 (-24), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 38559 to 38628 (+69), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 38559 to 39512 (+953), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 39512 to 39573 (+61), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 38559 to 37083 (-1476), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 37083 to 38567 (+1484), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 38567 to 39573 (+1006), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +0 against the trunk's own pin of 39573 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +1006 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 39573 to 26066 (-13507), a library's Prolog half
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
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 26022..26066 (spread 44) over 24 observations,
#: replacing a point pin of 26066. Its count is the scheduler's, its cost
#: follows the git repository it imports from, so the envelope is exact extrema
#: and a run outside it is a re-observation under --observe, not a re-pin
#: [measured 2026-09-09: python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10, twice, beside the plain lane runs ai-tmp records;
#: fixture=full-lane/277/workers=32; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: POOLED 2026-09-09: published 26022..26066 over 24
#: observations, receipt pass 26074..26149 over 10, and
#: final pass 26074..26149 over 10. Exact extrema and counts
#: retain the existing empirical protocol; no point budget becomes an envelope.
#: [measured: two complete ten-round passes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: RE-OBSERVED 2026-09-10 after setting the file-search cache lifetime
#: before engine creation. This complete ten-round population uses
#: 26074..26074 over 10 observations. Earlier protocol
#: samples remain above as history and do not enter this envelope.
#: [measured: all 277 pairs, this twin succeeds in every round; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: POOLED 2026-09-10: the earlier before-boot population has 26074..26074 over
#: ten samples; the receipt-frame repair's complete population has 26074..26074
#: over ten. The full lanes at 17bec75f1 and e70deddaa add 26074 and 26074.
#: Their exact pooled extrema are 26074..26074 over 22 observations under the
#: same cache-normalised protocol. Earlier runtime samples remain identified
#: separately; the receipt watcher now transfers ownership at live completion.
#: No point becomes an envelope. The final gate is an independent validation
#: sample [measured 2026-09-10: two complete ten-round populations and two full
#: lane checks; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: the retained 22 observations have 26074..26074. The full
#: lane at 71535ae17 adds 26074; a further complete ten-round population at
#: db8640733 adds 26074..26074. All 2770 new samples succeed. Exact pooled
#: extrema are 26074..26074 over 33 observations under the same before-boot
#: cache protocol. No point becomes an envelope [measured 2026-09-10: three
#: complete ten-round populations and three full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: retain the previous33 observations and both full-gate
#: samples (3fb950149: 26074; 503e21f8a: 26074), then append the complete ten-
#: round populations (2f1be07e9: 26074..26074; e93f2028d: 26074..26074). Both
#: populations have2770 successful samples, no failures and no point movements
#: or excursions. The e93f2028d population measures the repaired concurrent
#: join; the2f1be07e9 observation retains its own version. Exact pooled extrema
#: are26074..26074 over55 samples, without padding. No point becomes an
#: envelope. [measured 2026-09-10: five complete ten-round populations and five
#: full-lane readings; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-11: keep all 55 previous observations, append the two
#: complete gate readings (895878bbe=26074, 4d4fa2c55=26073), then all ten
#: qualified 4d4fa2c55 rounds (26073..26073). The resulting 67 observations
#: have exact extrema 26073..26074. The git-import low removes one inherited-
#: resolution retry through the explicit filereader:source_pending_definition/2
#: call. The same-path targeted toggle 26082/26081 establishes that delta and
#: does not enter this population. No targeted or instrumented reading enters
#: an envelope. The end-of-wave battery re-observes and re-pins the whole lane
#: on the merged tree under this protocol, pooling every empirical extension
#: with its count and mechanism. [measured 2026-09-11: six complete ten-round
#: populations and seven full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-ENVELOPED 2026-09-11 under 'full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot': the lane grew from 277 to 282 twinned
#: examples (the REDS corpus example and the wave's own), and the merged tree
#: carries FROM's reference rows, BINDING's one native evaluation entry,
#: W-OBSERVE's observer guard, PERF's receipts batching and cursor retirement,
#: and the REDS shared loader; ten fresh full-lane observations read
#: 26247..26247 (spread 0, samples [26247, 26247, 26247, 26247, 26247, 26247,
#: 26247, 26247, 26247, 26247]) where the 67 under 'full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot'
#: read 26073..26074. A run outside this envelope is a real finding, and a new
#: mode discovered later extends it with its observation count rather than
#: widening blind [measured 2026-09-11: exact extrema over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds
#: 10; fixture=full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: POOLED 2026-09-11: a second ten-round population under the same protocol,
#: taken on the tree that carries engine/metta/limits.pl and the re-pinned
#: twins, read 26256..26256 (samples [26256, 26256, 26256, 26256, 26256,
#: 26256, 26256, 26256, 26256, 26256]); pooled with the 10 above at
#: 26247..26247, 26247..26256 over 20 observations [measured 2026-09-11: exact
#: extrema over 10 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
#: RE-OBSERVED 2026-09-18 under 'full-lane/293/workers=32', 26073..26074 over
#: 67 under 'full-lane/277/workers=32' to 30508..30508 over 10: the branch's
#: tip f06186a96 after the landings the point re-pin names (the compiled call
#: law, the one codec at the grounded call, the runnable cache's dependency
#: index written by the producer, the host patches of 09-17, the class units)
#: and a corpus of 293 twinned examples under the lane's 32-worker pool, so the
#: scheduler this counter answers to is a new one and the observations are this
#: tree's own rather than pooled with the earlier protocol's [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10, wt-battery-6 ai-tmp/ai-observe-f06186a96.log; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 30508..30508 over
#: 10 under 'full-lane/293/workers=32' to 30508..30508 over 10: the corpus grew
#: from 293 to 294 twinned examples when 08-guarded_rules joined it
#: (49478d67a), and a full-lane protocol names the corpus width because the
#: scheduler this counter answers to is the whole corpus under the lane's
#: 32-worker pool, so the observations are this tree's own rather than pooled
#: with the earlier protocol's [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, wt-battery-5
#: ai-tmp/ai-observe-558f40c9c.log; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 30508..30508 over
#: 10 under 'full-lane/294/workers=32' to 30508..30508 over 23: every full-lane
#: run under one protocol is an observation, so the envelope pools the two ten-
#: round observations on this tree with the three full-lane runs that measured
#: it (the K5 tip's lane, the assembled tree before its envelopes and after),
#: the union of the extrema over the sum of the counts, as the 2026-09-08 entry
#: pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins three times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 30508..30508 over
#: 23 under 'full-lane/294/workers=32' to 30508..30508 over 24: every full-lane
#: run under one protocol is an observation, so the envelope pools the two ten-
#: round observations on this tree with the four full-lane runs that measured
#: it (the K5 tip's lane, the assembled tree before its envelopes, after them,
#: and after the first pooling), the union of the extrema over the sum of the
#: counts, as the 2026-09-08 entry pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins four times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log, ai-twins-K6-final-2.log; commit=bf5f100591493a91324b1d7552b5ad2731601691].
#: RE-OBSERVED 2026-09-18 under 'full-lane/294/workers=32', 30508..30508 over
#: 24 under 'full-lane/294/workers=32' to 30508..30508 over 25: every full-lane
#: run under one protocol is an observation, so the envelope pools the two ten-
#: round observations on this tree with the five full-lane runs that measured
#: it (the K5 tip's lane, the assembled tree before its envelopes, after them,
#: after the first pooling, and the tip e28c4f2f5 beside a second battery), the
#: union of the extrema over the sum of the counts, as the 2026-09-08 entry
#: pools two runs [measured 2026-09-18: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 twice and
#: GATE_ONLY=1 sh check.sh twins five times, ai-observe-558f40c9c.log, ai-
#: observe-c6448858b.log, ai-twins-K5.log, ai-twins-K6-interim.log, ai-
#: twins-K6-final.log, ai-twins-K6-final-2.log, ai-twins-tip-e28c4f2f5.log;
#: commit=0e767924501d8b25d1994f128d96c503d867e408].
BUDGET = {
    "minimum": 30508,
    "maximum": 30508,
    "observations": 25,
    "protocol": "full-lane/294/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
