"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/18-pln_formulas.metta in Python: PLN's arithmetic, and the helpers it stands on.

PLN and NARS share several NAMES -- `Truth_Revision`, `Truth_Negation`,
`Truth_Abduction` -- and they are different functions with different arities,
so a program imports one library or the other and never both. Every name keeps
its underscore, so every one comes through the exact subscript door.

`/safe` answers NOTHING on a zero denominator rather than raising, which is
how a formula whose preconditions fail contributes no answer: an empty list
is that absence in Python.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, lib

#: The truth value most five-argument formulas are asked about.
HALF = S.stv(0.5, 0.9)


def twin(m):
    """The helpers, the tuple operations, and each truth formula once."""
    m += lib.pln
    f = m.fn

    # The division every formula goes through.
    assert f["/safe"](1.0, 2.0) == [0.5]
    assert f["/safe"](1.0, 0.0) == []
    assert f["negate"](0.25) == [0.75]
    assert f["invert"](4.0) == [0.25]
    assert f["invert"](0.0) == []

    # The five-argument spellings, written out because MeTTa's `and` and
    # `min` are binary.
    assert f["and5"](TRUE, TRUE, TRUE, TRUE, TRUE) == [True]
    assert f["and5"](TRUE, TRUE, FALSE, TRUE, TRUE) == [False]
    assert f["min5"](5, 3, 9, 1, 7) == [1]

    # The tuple helpers, each naming what the reasoner means by an engine
    # operation.
    assert f["TupleCount"]((S.a, S.b, S.c)) == [3]
    assert f["TupleCount"](()) == [0]
    assert f["Without"]((1, 2, 3, 2), 2) == [(1, 3)]
    assert f["ElementOf"](2, (1, 2, 3)) == [True]
    assert f["ElementOf"](9, (1, 2, 3)) == [False]
    assert f["Unique"]((1, 2, 1, 3), ()) == [(1, 2, 3)]

    # Insertion, and the sort built on it.
    assert f["InsertSorted"](3, ()) == [(3,)]
    assert f["InsertSorted"](3, (1, 5)) == [(1, 3, 5)]
    assert f["InsertSorted"](0, (1, 5)) == [(0, 1, 5)]
    assert f["InsertionSort"]((3, 1, 2), ()) == [(1, 2, 3)]

    # The library's own comparison form, reporting both sides and the verdict
    # as DATA rather than raising.
    assert f["Test2"](1, 1) == [(S["Is:"](1), S["Should:"](1), S["Passed:"](TRUE))]
    assert f["Test2"](1, 2) == [(S["Is:"](1), S["Should:"](2), S["Passed:"](FALSE))]

    # The guard on the conjunction rule.
    consistent = f["Consistency_ImplicationImplicantConjunction"]
    assert consistent(0.5, 0.5, 0.5, 0.5, 0.5) == [True]
    assert consistent(0.0, 0.5, 0.5, 0.5, 0.5) == [False]
    assert consistent(0.5, 0.5, 0.1, 0.5, 0.5) == [False]

    # The evidence map, through `/safe`, so a confidence of exactly one
    # answers nothing rather than dividing by zero.
    assert f["Truth_w2c"](9.0) == [0.9]
    assert abs(f["Truth_c2w"](0.9)[0].value - 9.0) < 1e-9
    assert f["Truth_c2w"](1.0) == []

    assert f["Truth_Negation"](S.stv(0.8, 0.9)) == [S.stv(0.19999999999999996, 0.9)]

    # Revision merges two beliefs by adding their evidence, exactly as in
    # NARS except that PLN's ceiling is 1.0 rather than 0.99.
    assert f["Truth_Revision"](S.stv(1.0, 0.9), S.stv(0.0, 0.9)) == [
        S.stv(0.5, 0.9473684210526316)
    ]

    # Modus ponens over a SYMMETRIC link, where the rule cannot assume a
    # direction and carries a fixed 0.2 for the negative branch.
    assert f["Truth_SymmetricModusPonens"](S.stv(1.0, 0.9), S.stv(1.0, 0.8)) == [
        S.stv(1.0, 0.8)
    ]

    # The guard deciding which links that rule may fire on: three equations
    # rather than a list, so a link type it does not name answers NOTHING.
    guard = f["SymmetricModusPonensRuleGuard"]
    assert guard(S.Similarity) == [True]
    assert guard(S.IntentionalSimilarity) == [True]
    assert guard(S.ExtensionalSimilarity) == [True]
    assert guard(S.Inheritance) == []

    # Inversion keeps the strength and penalises the confidence by a fixed
    # 0.6, which the library records as weaker than classic OpenCog PLN.
    assert f["Truth_inversion"](HALF, S.stv(0.8, 0.9)) == [
        S.stv(0.8, 0.48600000000000004)
    ]

    # Equivalence to implication, through the PLN book's sim2inh formula.
    assert f["Truth_equivalenceToImplication"](HALF, HALF, S.stv(0.8, 0.9)) == [
        S.stv(0.888888888888889, 0.9)
    ]

    # The strength half of transitive similarity, and that strength with the
    # weaker of the two confidences.
    assert f["TransitiveSimilarityStrength"](0.5, 0.5, 0.5, 0.5, 0.5) == [
        0.3846153846153847
    ]
    assert f["Truth_transitiveSimilarity"](
        HALF, HALF, HALF, S.stv(0.5, 0.8), S.stv(0.5, 0.7)
    ) == [S.stv(0.3846153846153847, 0.7)]

    # Deduction's strength, and where the consistency guard bites: failed
    # preconditions answer NOTHING, so the rule derives nothing rather than
    # something unjustified.
    assert f["simpleDeductionStrength"](0.5, 0.5, 0.5, 0.5, 0.5) == [0.5]
    assert f["simpleDeductionStrength"](0.0, 0.5, 0.5, 0.5, 0.5) == []

    # That strength with a confidence discounted twice by 0.9.
    assert f["Truth_evaluationImplication"](HALF, HALF, HALF, HALF, HALF) == [
        S.stv(0.5, 0.6561000000000001)
    ]

    # PLN's induction and abduction take FIVE truth values where NARS's take
    # two, because these formulas need the node probabilities as well.
    weakened = S.stv(0.5, 0.4736842105263158)
    assert f["Truth_Induction"](HALF, HALF, HALF, HALF, HALF) == [weakened]
    assert f["Truth_Abduction"](HALF, HALF, HALF, HALF, HALF) == [weakened]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 171861 inferences, 0.9798x the example's 175406; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 171861 to 171918 (+57), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 171918 to 171746 (-172), metta_substitute_self/3
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
#: RE-PINNED 2026-09-08, 171746 to 171633 (-113), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 171633 to 171645 (+12), boot content moved: the
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
#: RE-PINNED 2026-09-08, 171633 to 174856 (+3223), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 174856 to 174865 (+9), The engine and library module
#: boundaries retain explicit lookup owners, including host registration and
#: returned callback goals [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 174865 to 175549 (+684), the module boundary merged
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
#: RE-PINNED 2026-09-08, 171645 to 171683 (+38), The typed host door catalog is
#: published before user code. Its declarations change catalog lookup indexes;
#: generated public names bind directly to their existing bodies [measured
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 171683 to 175567 (+3884), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 175567 to 176305 (+738), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 175549 to 178147 (+2598), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 178147 to 178906 (+759), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 175549 to 175504 (-45), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 175504 to 178867 (+3363), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -39 against the trunk's own pin of 178906 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +3402 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 178867 to 178890 (+23), a library's Prolog half
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
#: RE-PINNED 2026-09-10, 178890 to 178488 (-402), the binding resolves Janus
#: maplist/2 at boot, removing its first-failure autoload; one compiled option
#: policy removes repeated evaluation frames, and keyed dispatch removes
#: repeated transport/context selection. Indexed source-macro hooks preserve
#: unrelated compilation costs. Same-cut controls and all before/after rows are
#: in docs/journal/2026-09-09-the-binding-collapse.md. These three fresh serial
#: processes set file_search_cache_time=9223372036854775807 before boot,
#: matching the validated full-lane/277/workers=32/file-cache-
#: time=9223372036854775807 environment. Workloads, point tolerances and
#: empirical envelopes are unchanged [measured 2026-09-10: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
#: RE-PINNED 2026-09-10, 178488 to 178503 (+15), automatic memo reconciliation
#: uses a trailed marker so an inference-limit signal cannot leak its guard.
#: The ordinary dirty drain saves two inferences; the first unset-marker read
#: in each engine invokes SWI's undefined-global hook. Removing the old thread-
#: local predicate also changes catalog-arity enumeration order: five
#: inferences per visited arity in metta_catalog_clause/2 or the partial-list
#: get_native_atom/3 lookup. Same-worktree old/current/restore measurements,
#: native call-site coverage and actual missing-global events separate those
#: costs. See docs/journal/2026-09-09-the-binding-collapse.md. These are three
#: fresh sequential samples per row with 32 concurrent row runners, warmed
#: library artifacts, and file_search_cache_time=9223372036854775807 before
#: boot. Every workload, point allowance and empirical envelope is unchanged
#: [measured 2026-09-10: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
BUDGET = 178503
