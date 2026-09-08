"""examples/ch08-data/08-03-the-shipped-libraries/11-combinatorics_lib.metta in Python: choosing from a finite collection.

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
#: RE-PINNED 2026-09-08, 119605 to 119728 (+123), Compiled shipped typing
#: decisions and initial vocabulary facts remove repeated interpretation;
#: indexed vocabulary membership replaces member-list scans; catalog reference
#: checks now respect transaction-local erasure. Paired controls and cut counts
#: are recorded in docs/journal/2026-09-08-what-the-waivers-were-paying-for.md
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=32650f9ff4d1c4aa0749d8eb8b153e5bb448ee5c].
BUDGET = 119728
