"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/11-combinatorics_lib.metta in Python: choosing from a finite collection.

Each operation comes in two shapes, a nondeterministic one answering a choice
per solution and an `l` one answering the whole tuple, and Python reads the
first as a LIST of answers and the second as one answer that IS a list. That
is the same distinction, written the way each language writes it.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

#: The collection every claim is about, and its three unordered pairs.
LETTERS = (S.a, S.b, S.c)
PAIRS = ((S.a, S.b), (S.a, S.c), (S.b, S.c))


def twin(m):
    """Pairs, k-subsets in both shapes, and the prefix that is neither."""
    m += lib.combinatorics
    two, two_list = m.fn.choose2, m.fn.choose2l
    k_list, k_stream, prefix = m.fn.chooseKl, m.fn.chooseK, m.fn.takeK

    # Every unordered pair, one per solution: (a b) but never (b a), and
    # never (a a).
    assert sorted(two(LETTERS), key=str) == list(PAIRS)
    assert two((S.a,)) == []
    assert two(()) == []

    # The same answer set as one value rather than as multiplicity.
    assert two_list(LETTERS) == [PAIRS]
    assert two_list((S.a,)) == [()]

    # k of them, still unordered, still without repetition, in the list's own
    # order because the recursion counts down through it.
    assert k_list(LETTERS, 2) == [PAIRS]
    assert k_list((S.a, S.b, S.c, S.d), 3) == [
        ((S.a, S.b, S.c), (S.a, S.b, S.d), (S.a, S.c, S.d), (S.b, S.c, S.d))
    ]
    assert k_list(LETTERS, 2) == two_list(LETTERS)

    # The two base cases that make the recursion total: choosing none of
    # anything is one choice, the empty one, and choosing some of nothing is
    # no choice at all.
    assert k_list(LETTERS, 0) == [((),)]
    assert k_list((), 2) == [()]
    assert k_list((), 0) == [((),)]

    # The streamed version, which is what a search wants: the consumer can
    # stop without the rest being built.
    assert sorted(k_stream(LETTERS, 2), key=str) == list(PAIRS)
    assert k_stream(LETTERS, 0) == [()]

    # `takeK` is the prefix rather than a choice: the first k in order, and
    # the whole list when there are fewer than k.
    assert prefix(2, LETTERS) == [(S.a, S.b)]
    assert prefix(0, LETTERS) == [()]
    assert prefix(5, LETTERS) == [LETTERS]
    assert prefix(2, ()) == [()]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 119167 inferences, 1.0981x the example's 108518; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 119167 to 119116 (-51), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 119116 to 117376 (-1740), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 117376 to 119336 (+1960), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 119336 to 119605 (+269), the module boundary merged
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
#: RE-PINNED 2026-09-09, 119605 to 119929 (+324), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 119605 to 121384 (+1779), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 121384 to 121708 (+324), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 119605 to 119728 (+123), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 119728 to 121831 (+2103), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, +123 against the trunk's own pin of 121708 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +1980 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-09, 121831 to 87047 (-34784), a library's Prolog half
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
#: RE-PINNED 2026-09-10, 87047 to 86991 (-56), the binding resolves Janus
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
#: RE-PINNED 2026-09-11, 86991 to 87957 (+966), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 86991 to 90172 (+3181), the branch's landings since
#: the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 90172 to 89557 (-615), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=55d451b670949c2dc9d2ab7bc678f33f21094bd2].
BUDGET = 89557
#: OVERRUN 2026-09-09, 0 to 242 (+242): the compiled vocabulary seed, the
#: membership index, base-module type lookups and the singleton decoder landed
#: (perf/cross-engine-waivers merged): a Python decode with one named variable
#: builds no index and one with more builds it at the second distinct name,
#: which moves a twin's engine-side cost while its example, which decodes
#: nothing, holds; boot content and clause layout moved the rest; against the
#: trunk's own run at da0e5755d the twin moved +123 and the example +141, and
#: the twin sat 273 over its ceiling there already. Measured 121831 against a
#: ceiling of 121590; a minimal twin costs 110063 against the band's 121590,
#: within that ceiling, so the rest is this twin's own program [measured
#: 2026-09-09: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: OVERRUN 2026-09-09, 242 to 3637 (+3395): a library's Prolog half compiles
#: beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): the example imports one, so
#: the import's consult and its compile-time expansion left both sides in
#: equal measure and the tenth of it that padded this twin's ceiling left with
#: them, which shows the twin's own excess whole; the lane's authoring
#: constants are re-derived on this tree in the same change; against the run
#: before the compiled halves (b4341ae38) the twin moved -34784 and the
#: example -34708, and the twin sat 1 within its ceiling there. Measured 87047
#: against a ceiling of 87048; a minimal twin costs 75354 against the band's
#: 83411, within that ceiling, so the rest is this twin's own program
#: [measured 2026-09-09: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py;
#: commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: OVERRUN 2026-09-10, 3637 to 3945: The existing program is priced after the
#: reference census, ordered catalog reads and source-scoped translation
#: work. It costs 87974 against the unchanged band and authoring ceiling of
#: 84029.0. The literal structured control costs 76429; it measures that
#: encoding only. [measured 2026-09-10: one fresh process per side;
#: command=python extensions/python/benchmarks/probes/twin_floor.py
#: examples/ch08-data/08-03-the-shipped-libraries/11-combinatorics_lib.metta;
#: commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
OVERRUN = 3945
