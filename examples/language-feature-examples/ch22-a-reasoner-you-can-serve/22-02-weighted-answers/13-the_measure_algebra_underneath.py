"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/13-the_measure_algebra_underneath.metta in Python: the five steps the measure algebra folds.

A weighted superposition is a tuple of `(weight value)` pairs, so every
argument here is an ordinary Python tuple of atoms and every claim is one
call. `ws-sample-walk` takes the random budget EXPLICITLY, which is what
makes a sampling step testable at all.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

#: The three pairs most claims are about, and the ranked order of them.
UNRANKED = ((0.2, S.low), (0.7, S.high), (0.1, S.mid))
RANKED = ((0.7, S.high), (0.2, S.low), (0.1, S.mid))


def twin(m):
    """Rank, take, pick, walk and merge, then the surface built on them."""
    m += lib.measure
    ranked, take = m.fn["ws-ranked"], m.fn["ws-take"]
    pickmax, walk = m.fn["ws-pickmax"], m.fn["ws-sample-walk"]
    merge = m.fn["ws-merge-into"]

    # The ordering: pairs best-first, by the standard order of terms with the
    # weight written first.
    assert ranked(UNRANKED) == [RANKED]
    assert ranked(()) == [()]

    # Beam search's keep rule, total in both directions.
    assert take(RANKED, 2) == [RANKED[:2]]
    assert take(((0.7, S.high),), 5) == [((0.7, S.high),)]
    assert take(RANKED[:2], 0) == [()]
    assert take((), 2) == [()]

    # `ws-top` is those two composed.
    assert m.fn["ws-top"](UNRANKED, 2) == take(ranked(UNRANKED)[0], 2)

    # The step `ws-best` folds with: the heavier of two pairs, and the FIRST
    # of two equal ones, which is what makes the fold deterministic on ties.
    assert pickmax((0.2, S.a), (0.7, S.b)) == [(0.7, S.b)]
    assert pickmax((0.7, S.b), (0.2, S.a)) == [(0.7, S.b)]
    assert pickmax((0.5, S.a), (0.5, S.b)) == [(0.5, S.a)]

    # The inverse-transform step under `ws-sample!`, with the randomness
    # taken out: it walks the pairs subtracting weights until the budget runs
    # out.
    distribution = ((0.5, S.a), (0.3, S.b), (0.2, S.c))
    assert walk(distribution, 0.1) == [S.a]
    assert walk(distribution, 0.6) == [S.b]
    assert walk(distribution, 0.9) == [S.c]

    # The last pair absorbs everything left over, so a budget past the total
    # mass still lands on a value.
    assert walk(((0.5, S.a), (0.5, S.b)), 1.5) == [S.b]

    # The step `ws-collapse` folds with: add one pair, summing weights where
    # the VALUE already appears and appending where it does not.
    assert merge((), (0.3, S.x)) == [((0.3, S.x),)]
    assert merge(((0.3, S.x), (0.4, S.y)), (0.2, S.x)) == [((0.5, S.x), (0.4, S.y))]
    assert merge(((0.3, S.x),), (0.2, S.z)) == [((0.3, S.x), (0.2, S.z))]

    # And the fold over it is `ws-collapse`, so the surface operation is this
    # step and nothing else.
    folded = merge(merge(merge((), (0.3, S.x))[0], (0.4, S.y))[0], (0.2, S.x))
    assert m.fn["ws-collapse"](((0.3, S.x), (0.4, S.y), (0.2, S.x))) == folded


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 44683 inferences, 1.0644x the example's 41978; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 44683 to 44647 (-36), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 44647 to 42881 (-1766), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 42881 to 43235 (+354), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 43235 to 43560 (+325), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 43560 to 43969 (+409), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 43560 to 44241 (+681), Trailing occurrence arguments,
#: token allocation in native writes, exact source withdrawal and transaction-
#: safe shared-table guards change the engine work priced by this twin; answer
#: bags retain the upstream law [measured 2026-09-08: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 44241 to 44650 (+409), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 43560 to 43604 (+44), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 43604 to 44694 (+1090), the compiled vocabulary seed,
#: the membership index, base-module type lookups and the singleton decoder
#: landed (perf/cross-engine-waivers merged): boot publishes the initial
#: vocabulary types from a compiled payload through the tokenized funnel, a
#: warm membership read touches only its own clauses, a base-module type lookup
#: skips the prelude, and a Python decode with one named variable builds no
#: index; per-operation costs of a mint, write, read, drop, run, save and load
#: are unchanged against the trunk in fresh processes; measured on the merged
#: tree, +44 against the trunk's own pin of 44650 at da0e5755d; the previous
#: number is the branch's cut-time price, and the remaining +1046 is what
#: landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 44694 to 44614 (-80), the binding resolves Janus
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
#: RE-PINNED 2026-09-10, 44614 to 44621 (+7), automatic memo reconciliation
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
#: RE-PINNED 2026-09-11, 44621 to 45241 (+620), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
BUDGET = 45241
