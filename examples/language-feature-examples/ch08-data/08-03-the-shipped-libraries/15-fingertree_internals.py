"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/15-fingertree_internals.metta in Python: the 2-3 finger tree from the inside.

A tree is one of three constructors and they are ordinary data, so a tree can
be written out by hand as an atom and read back with the same operations that
build one. `FTEmpty` is a VALUE, written bare, because it takes nothing; the
four declarations behind the three are read back in chapter 9's
`21-a_librarys_declared_types`.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

EMPTY = S.FTEmpty


def twin(m):
    """Constructors, the borrow pair, the regrouping, and concatenation."""
    m += lib.datastructures
    to_list, from_list = m.fn["ft-to-list"], m.fn["ft-from-list"]
    digit, nodes = m.fn["ft-node-digit"], m.fn["ft-nodes"]
    borrow_l, borrow_r = m.fn["ft-borrow-l"], m.fn["ft-borrow-r"]
    push_front, push_back = m.fn["ft-push-list-front"], m.fn["ft-push-list-back"]
    app3 = m.fn["ft-app3"]

    assert to_list(S.FTSingle(1)) == [(1,)]
    assert to_list(S.FTDeep((1, 2), EMPTY, (3, 4))) == [(1, 2, 3, 4)]
    assert m.fn["ft-is-empty"](EMPTY) == [True]
    assert m.fn["ft-is-empty"](S.FTSingle(1)) == [False]

    # A node re-enters the shallower level as a digit.
    assert digit(S.FTNode2(S.a, S.b)) == [(S.a, S.b)]
    assert digit(S.FTNode3(S.a, S.b, S.c)) == [(S.a, S.b, S.c)]

    # The pop that empties a prefix: with an empty middle it redistributes
    # the suffix, and with a nonempty one it borrows a node from the front.
    assert borrow_l(EMPTY, (S.a,)) == [S.FTSingle(S.a)]
    assert borrow_l(EMPTY, (S.a, S.b)) == [S.FTDeep((S.a,), EMPTY, (S.b,))]
    assert borrow_l(EMPTY, (S.a, S.b, S.c, S.d)) == [
        S.FTDeep((S.a, S.b), EMPTY, (S.c, S.d))
    ]
    assert borrow_l(S.FTSingle(S.FTNode2(S.a, S.b)), (S.c,)) == [
        S.FTDeep((S.a, S.b), EMPTY, (S.c,))
    ]

    # Its mirror on the suffix, taking its arguments in the mirrored order.
    assert borrow_r((S.a,), EMPTY) == [S.FTSingle(S.a)]
    assert borrow_r((S.a, S.b), EMPTY) == [S.FTDeep((S.a,), EMPTY, (S.b,))]
    assert borrow_r((S.a,), S.FTSingle(S.FTNode2(S.b, S.c))) == [
        S.FTDeep((S.a,), EMPTY, (S.b, S.c))
    ]

    # Between them they are why a pop is amortized constant: the expensive
    # case moves ONE node one level.
    assert to_list(borrow_l(S.FTSingle(S.FTNode3(S.a, S.b, S.c)), (S.d,))[0]) == [
        (S.a, S.b, S.c, S.d)
    ]

    # The regrouping concatenation needs: loose elements become 2-3 nodes,
    # three at a time, so no node is ever a singleton.
    assert nodes((1, 2)) == [(S.FTNode2(1, 2),)]
    assert nodes((1, 2, 3)) == [(S.FTNode3(1, 2, 3),)]
    assert nodes((1, 2, 3, 4)) == [(S.FTNode2(1, 2), S.FTNode2(3, 4))]
    assert nodes((1, 2, 3, 4, 5)) == [(S.FTNode3(1, 2, 3), S.FTNode2(4, 5))]
    assert nodes((1, 2, 3, 4, 5, 6)) == [(S.FTNode3(1, 2, 3), S.FTNode3(4, 5, 6))]

    # Pushing a whole expression one element at a time, and the order each
    # ends up in.
    two = from_list((3, 4))[0]
    assert to_list(push_front((1, 2), two)[0]) == [(1, 2, 3, 4)]
    assert to_list(push_back((1, 2), two)[0]) == [(3, 4, 1, 2)]
    assert to_list(push_front((), two)[0]) == [(3, 4)]
    assert to_list(push_back((), two)[0]) == [(3, 4)]

    # The operation finger trees exist for: two trees and a list of loose
    # elements between them, joined in O(log n).
    left = from_list((1, 2))[0]
    assert to_list(app3(left, (7, 8), two)[0]) == [(1, 2, 7, 8, 3, 4)]
    assert to_list(app3(EMPTY, (7, 8), two)[0]) == [(7, 8, 3, 4)]
    assert to_list(app3(left, (), EMPTY)[0]) == [(1, 2)]
    assert to_list(app3(EMPTY, (), EMPTY)[0]) == [()]

    # `ft-concat` is `ft-app3` with nothing in the middle.
    assert to_list(m.fn["ft-concat"](left, two)[0]) == to_list(app3(left, (), two)[0])


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 208634 inferences, 1.0578x the example's 197230; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 208634 to 208404 (-230), metta_substitute_self/3
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
#: RE-PINNED 2026-09-08, 208404 to 206580 (-1824), the evaluation-fuel scope
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
#: RE-PINNED 2026-09-08, 206580 to 207024 (+444), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 207024 to 207575 (+551), the module boundary merged
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
#: RE-PINNED 2026-09-09, 207575 to 208307 (+732), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 207575 to 210380 (+2805), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 210380 to 211112 (+732), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-08, 207575 to 204754 (-2821), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
#: RE-PINNED 2026-09-09, 204754 to 208291 (+3537), the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): boot publishes the
#: initial vocabulary types from a compiled payload through the tokenized
#: funnel, a warm membership read touches only its own clauses, a base-module
#: type lookup skips the prelude, and a Python decode with one named variable
#: builds no index; per-operation costs of a mint, write, read, drop, run, save
#: and load are unchanged against the trunk in fresh processes; measured on the
#: merged tree, -2821 against the trunk's own pin of 211112 at da0e5755d; the
#: previous number is the branch's cut-time price, and the remaining +6358 is
#: what landed on the trunk between the cut f0d33dcad and da0e5755d, tokens as
#: storage above all [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
#: RE-PINNED 2026-09-10, 208291 to 208128 (-163), the binding resolves Janus
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
#: RE-PINNED 2026-09-10, 208128 to 208121 (-7), automatic memo reconciliation
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
#: RE-PINNED 2026-09-11, 208121 to 209209 (+1088), end-of-wave re-pin on the
#: merged tree after FROM's reference rows and four engine units, the closed-
#: set derivations and two host services, BINDING's one native evaluation entry
#: and boot import, W-OBSERVE's observer guard, PERF's receipts batching and
#: cursor retirement, and the three REDS repairs (derived runtime resources and
#: the shared loader, the tool-lane repairs, the corpus example); serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-11: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: RE-PINNED 2026-09-18, 208121 to 213813 (+5692), the branch's landings since
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
#: RE-PINNED 2026-09-18, 213813 to 210301 (-3512), the trunk merged (f97c4b0a3,
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
BUDGET = 210301
