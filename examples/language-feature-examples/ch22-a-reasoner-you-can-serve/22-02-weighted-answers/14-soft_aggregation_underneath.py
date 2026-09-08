"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/14-soft_aggregation_underneath.metta in Python: how a soft score walks a term.

The similarity facts are ordinary atoms written into the space, and the
aggregation is chosen by NAME, so `S.min` and `S.mean` are symbols rather
than Python callables: the fold dispatches on the name it is handed.

`soft-symbol?` tests the WRITTEN representation rather than the metatype,
which is why `min` answers True: a metatype test would answer False for every
name the engine holds a function for.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib


def twin(m):
    """A symbol test, two aggregations, and the walk under each."""
    m += lib.soft
    m += [S.similar(S.cat, S.feline, 0.8), S.similar(S.fish, S.shark, 0.5)]
    symbol, fold, walk = m.fn["soft-symbol?"], m.fn["soft-fold"], m.fn["soft-walk"]

    assert symbol(S.cat) == [True]
    assert symbol(S.min) == [True]
    assert symbol(1) == [False]
    assert symbol(G("text")) == [False]
    assert symbol(S.f(1)) == [False]

    # `min` is the fuzzy t-norm, so a term is as close as its WORST position.
    assert fold(S.min, (S.cat, S.fish), (S.feline, S.fish)) == [0.8]
    assert fold(S.min, (S.cat, S.fish), (S.feline, S.shark)) == [0.5]
    assert fold(S.min, (S.cat, S.fish), (S.dog, S.fish)) == [0.0]
    assert fold(S.min, (S.cat, S.fish), (S.cat, S.fish)) == [1.0]

    # `mean` averages instead, which is the aggregation ranking wants: one
    # unrelated symbol takes a strong match to zero under `min` and to a
    # middling number under `mean`.
    assert fold(S.mean, (S.cat, S.fish), (S.feline, S.shark)) == [0.65]
    assert fold(S.mean, (S.cat, S.fish), (S.dog, S.fish)) == [0.5]

    # The walk is the recursion each fold runs, with the accumulator exposed:
    # `min` starts at 1.0 and takes minima, `mean` starts at 0.0 and SUMS.
    assert walk(S.min, (S.cat, S.fish), (S.feline, S.shark), 1.0) == [0.5]
    assert walk(S.mean, (S.cat, S.fish), (S.feline, S.shark), 0.0) == [1.3]
    assert fold(S.mean, (S.cat, S.fish), (S.feline, S.shark))[0].value == (
        walk(S.mean, (S.cat, S.fish), (S.feline, S.shark), 0.0)[0].value / 2
    )

    # Which is where `min`'s early stop lives: once the accumulator is 0.0 no
    # later position can raise it, so the positions after the mismatch are
    # never scored.
    assert walk(S.min, (S.dog, S.whale, S.otter), (S.cat, S.shark, S.seal), 1.0) == [0.0]
    assert walk(S.min, (S.dog, S.whale), (S.cat, S.shark), 0.0) == [0.0]

    # Both walks over nothing answer the accumulator they were given.
    assert walk(S.min, (), (), 1.0) == [1.0]
    assert walk(S.mean, (), (), 0.0) == [0.0]

    # And the aggregation a space DECLARES is what `soft-score` folds with.
    assert m.fn["soft-score"](S.likes(S.cat, S.fish), S.likes(S.feline, S.shark)) == [0.5]
    m += S.soft_aggregate(S.mean)
    assert m.fn["soft-score"](
        S.likes(S.cat, S.fish), S.likes(S.feline, S.shark)
    ) == fold(S.mean, S.likes(S.cat, S.fish), S.likes(S.feline, S.shark))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 138416 inferences, 1.0160x the example's 136240; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 138416 to 138421 (+5), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 138421 to 138373 (-48), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 138373 to 136615 (-1758), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 136615 to 137476 (+861), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 137476 to 137791 (+315), the module boundary merged
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
#: RE-PINNED 2026-09-09, 137791 to 138183 (+392), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 137791 to 140434 (+2643), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 140434 to 140826 (+392), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 137791 to 137602 (-189), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 137602 to 140636 (+3034), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -190 against the trunk's own pin of 140826 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +3224 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 140636 to 125553 (-15083), a library's Prolog half
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
BUDGET = 125553
