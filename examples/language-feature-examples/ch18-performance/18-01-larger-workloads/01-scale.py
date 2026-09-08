"""Purpose: examples/ch18-performance/18-01-larger-workloads/01-scale.metta in Python: a million atoms, five index shapes.

`addK` bulk-loads a million `(r K (mod K 10))` atoms, and five query shapes then
ask the same store different questions: everything, a bound first argument, a
bound second, both bound, and a variable in HEAD position. The driver runs all
five and reports the counts, which is the claim.

The driver is an ordinary Python function under the decorator: it calls its six
siblings by name through the mention door and builds the report it answers.

Two families stay at the container door, each for a blocker rather than a
preference.

The five queries are `(collapse (match ...))`, and a compiled body has no
spelling for `collapse` at all: `list(...)` and `fn.collapse` are both refused,
and a comprehension over a match lowers to `map-atom`, a different operation,
`(map-atom (match ...) (|-> ($x) $x))`, answering once per solution where
collapse answers once [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT:
`list(space[pattern])` inside a body. Residue P14.4.

`addK` compiles and then cannot run. A compiled `if` wraps its condition in
`py-truthy` and `==` lowers to `py-eq`, so every level of this million-deep
recursion spends reductions the original does not, and the evaluator's default
100,000 stack bound is reached at K=100,000: the compiled `addK` answers
`(Error 75002 StackOverflow)` where the term door completes a million
[measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. `m.limits` bounds inferences and time
and not stack depth, so there is no scope to raise it in and the example states
no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone, or a stack-depth mode block. Residue P14.4 and P14.14.
"""

from metta import S, V, equation, fn, if_

#: What a million atoms answer to the five shapes, in the driver's own order.
REPORT = S["all:"](1_000_000, S["first:"], 1, S["second:"], 100_000,
                   S["rel:"], 1, S["both:"], 1)


def twin(m):
    """Load a million atoms, then ask five differently-shaped questions."""
    m += equation(S.addK(V.k)).to(
        if_(S.eq(V.k, 0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V.k10, V.k % 10),  # rung: as above
                           (V.written, S.add_atom(m, S.r(V.k, V.k10)))),  # rung: as above
                          S.addK(V.k - 1))))

    # Five shapes over one store: nothing bound, first bound, second bound,
    # both bound, and the relation itself a variable.
    m += equation(S.q_all()).to(S.collapse(S.match(m, S.r(V.x, V.y), S.r(V.x, V.y))))  # rung: a compiled body has no spelling for collapse
    m += equation(S.q_first(V.a)).to(S.collapse(S.match(m, S.r(V.a, V.y), S.r(V.a, V.y))))  # rung: as above
    m += equation(S.q_second(V.b)).to(S.collapse(S.match(m, S.r(V.x, V.b), S.r(V.x, V.b))))  # rung: as above
    m += equation(S.q_both(V.a, V.b)).to(S.collapse(S.match(m, S.r(V.a, V.b), S.r(V.a, V.b))))  # rung: as above
    m += equation(S.q_rel(V.r)).to(S.collapse(S.match(m, (V.r, 643, 3), (V.r, 643, 3))))  # rung: as above

    @m.define
    def indexing_demo(k):
        _loaded = fn.addK(k)
        everything = fn.q_all()
        first = fn.q_first(7)
        second = fn.q_second(3)
        rel = fn.q_rel(S.r)
        both = fn.q_both(42, 2)
        return S["all:"](fn.length(everything), S["first:"], fn.length(first),
                         S["second:"], fn.length(second), S["rel:"], fn.length(rel),
                         S["both:"], fn.length(both))

    assert indexing_demo(1_000_000) == [REPORT]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 26335504 to 26335523, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 26335523 to 26335529, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 26335529 to 26335496, on the release tree:
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
#: RE-PINNED 2026-08-25, 26335496 to 26335501, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 26335501 to 26335533 (+32), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 26335533 to 26335555 (+22), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 26335555 to 23218681 (-3116874), the compiled-language
#: batch: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 23218681 to 23218650 (-31), the subtract-atom
#: primitive and Counter's grain for -=: a new engine head shifts every twin's
#: load structure, the removal doors changed meaning where a twin spells one,
#: and the quad twin stopped being a different program [measured 2026-09-01:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 23218650 to 23218632 (-18), generic Python operators
#: now dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 23218632 to 23218842 (+210), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 23218842 to 23218870 (+28), static contract discharge
#: with policy checks confined to invalidated contracts [measured 2026-09-02:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 23218870 to 23218884 (+14), P43 protects both
#: generated policy-check fallbacks from space-local capture [measured
#: 2026-09-02: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 23218884 to 23217842 (-1042), the one pricing pass at
#: the 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 23217842 to 23218554 (+712), trunk's own movement
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
#: RE-PINNED 2026-09-08, 23218554 to 23218594 (+40), the merges between this
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
#: RE-PINNED 2026-09-08, 23218594 to 23218030 (-564), metta_substitute_self/3
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
#: RE-PINNED 2026-09-08, 23218030 to 23218044 (+14), boot content moved: the
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
#: RE-PINNED 2026-09-08, 23218030 to 23218097 (+67), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 23218097 to 23218107 (+10), The engine and library
#: module boundaries retain explicit lookup owners, including host registration
#: and returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 23218107 to 23218084 (-23), the module boundary merged
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
#: RE-PINNED 2026-09-08, 23218044 to 23218079 (+35), The typed host door
#: catalog is published before user code. Its declarations change catalog
#: lookup indexes; generated public names bind directly to their existing
#: bodies [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 23218079 to 23218104 (+25), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 23218104 to 23218132 (+28), structured concurrency
#: landed (feat/structured-concurrency merged at f80cc416d): every space mint
#: records its allocation in the library's lifetime rows, every write and run
#: pays the ownership hook and every drop asks the library whether a scope owns
#: the name, measured on a pristine control as 32 per mint, 2 per write and 44
#: per drop with none per read; measured on the merged tree [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 23218084 to 29218541 (+6000457), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-08, 29218541 to 29218481 (-60), Sharing the fast-image
#: hexadecimal validator changes the engine predicate layout. The identity twin
#: moves below its declared band while the seven engine work counters move only
#: at boot; the native add and read slopes remain unchanged. Token storage and
#: source ownership retain their earlier measured costs and answer bags
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 29218481 to 29218574 (+93), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 23218084 to 23218132 (+48), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 23218132 to 23218705 (+573), Compile shipped typing
#: decisions and initial vocabulary facts, index vocabulary membership, and
#: reuse the first Python variable binding before indexing additional names;
#: retain type, transaction and variable-identity checks [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 23218705 to 29219100 (+6000395), the compiled
#: vocabulary seed, the membership index, base-module type lookups and the
#: singleton decoder landed (perf/cross-engine-waivers merged): boot publishes
#: the initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, +526 against the trunk's own pin of 29218574 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +5999869
#: is what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens
#: as storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 29219100

#: DIVERGED 2026-09-07, the example holds 1000007 atoms and the twin 1000007,
#: over the 50000 this lane enumerates, so the difference is pinned as the two
#: digests: the twin is an ordinary Python program and its body lowers to the
#: engine's own forms: a match statement is ONE equation whose body is a case
#: tower where the example writes one clause per arm, a named intermediate is a
#: let* the original does not have, a Python truth test wraps its condition in
#: py-truthy, and the annotations and docstrings that come with it are stored
#: beside them [measured 2026-09-07: the two stored-atom surpluses, one fresh
#: process per side; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "45475e3c6b4bad84e8e1f4d6c887754c0906190103f1030b8b6fa759497c8ba2"
