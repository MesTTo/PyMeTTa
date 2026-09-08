"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/12-dict_lib.metta in Python: a dict IS a space.

Every operation is a write or a match, so the dict is a space HANDLE and
never a name written as text. `dict-put` WRITES rather than answering a new
dict, which is why the size claims below are about the same handle before and
after.

The last claim is the one no dictionary API offers: which key holds a given
value, asked as an ordinary pattern.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, lib


def twin(m):
    """Size, membership, values, put, remove, and a reverse lookup."""
    m += lib.dict
    prices = m.fn["dict-space"](((S.apple, 3), (S.pear, 5)))[0]
    size, has = m.fn["dict-size"], m.fn["dict-has"]
    values, pairs = m.fn["dict-values"], m.fn["dict-pairs"]
    put, remove = m.fn["dict-put"], m.fn["dict-remove"]
    remove_pair = m.fn["dict-remove-pair"]

    assert size(prices) == [2]
    assert has(prices, S.apple) == [True]
    assert has(prices, S.durian) == [False]

    # `dict-values` answers one value per key, which is nondeterminism rather
    # than a list; `dict-pairs` is the whole thing collapsed.
    assert sorted(v.value for v in values(prices)) == [3, 5]
    assert m.fn.sort_atom(pairs(prices)[0]) == [((S.apple, 3), (S.pear, 5))]

    # `dict-put` WRITES, and answers the same dict, because a space is a
    # handle and there is nothing else to answer.
    assert size(put(prices, S.plum, 7)[0]) == [3]
    assert size(prices) == [3]
    assert [row.v for row in prices[S.plum(V.v)]] == [7]

    # Putting a key that is there is a replacement, so a dict stays a map
    # rather than becoming a relation.
    assert size(put(prices, S.apple, 9)[0]) == [3]
    assert [row.v for row in prices[S.apple(V.v)]] == [9]

    # Removing a key that is not there is an ordinary answer rather than a
    # failure, which is what the collapse inside it is for.
    assert size(remove(prices, S.pear)[0]) == [2]
    assert has(prices, S.pear) == [False]
    assert size(remove(prices, S.durian)[0]) == [2]

    # The step under it: find the key's pair as a VALUE and remove exactly
    # it, answering the removal's own verdict per pair removed.
    assert remove_pair(prices, S.apple) == [True]
    assert has(prices, S.apple) == [False]
    assert remove_pair(prices, S.apple) == []

    # And because it is a space all along, the dict answers a pattern query
    # no dictionary API would offer.
    stock = m.fn["dict-space"](((S.apple, 12), (S.pear, 12), (S.plum, 4)))[0]
    assert sorted((row.k for row in stock[Expression((V.k, 12))]), key=str) == [
        S.apple,
        S.pear,
    ]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 95020 inferences, 0.9601x the example's 98965; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 95020 to 95025 (+5), the merges between this lane's
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
#: RE-PINNED 2026-09-08, 95025 to 94980 (-45), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 94980 to 94925 (-55), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 94925 to 98557 (+3632), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 98557 to 98878 (+321), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 98878 to 99366 (+488), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 98878 to 100578 (+1700), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 100578 to 101066 (+488), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
BUDGET = 101066
