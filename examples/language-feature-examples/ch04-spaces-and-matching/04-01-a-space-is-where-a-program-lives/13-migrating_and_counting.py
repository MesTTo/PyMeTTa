"""examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/13-migrating_and_counting.metta in Python: counting without listing, and a filtered drain.

`match-count` folds `+` over a match answering 1 per solution, so nothing is
materialised; a Python `len()` over the answer list would materialise exactly
what the operation exists to avoid, so this twin calls the operation.

`migrateAtoms` is measured rather than trusted here, because what it does is
not what its name says: the shipped equation names the SOURCE space on both
sides and never reads its destination argument.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, lib


def twin(m):
    """Count matches, then move atoms and see where they went."""
    m += lib.spaces
    ledger = m.metta.space(S.ledger)
    archive = m.metta.space(S.archive)
    ledger += [S.n(1), S.n(2), S.m(9)]

    count = m.fn["match-count"]
    assert count(ledger, S.n(V.x)) == [2]
    assert count(ledger, S.m(V.x)) == [1]
    assert count(ledger, S.zzz(V.x)) == [0]
    assert count(ledger, Expression((V.head, V.tail))) == [len(ledger)]

    # One pair of answers per atom moved, the answers of the two writes it
    # performs.
    assert m.fn.migrateAtoms(ledger, archive, S.n(V.x)) == [(True, True), (True, True)]

    # The matched atoms leave the source, and everything else stays.
    assert len(ledger) == 1
    assert count(ledger, S.n(V.x)) == [0]

    # THE DESTINATION IS NOT WRITTEN. The shipped equation names the source on
    # both sides, which is upstream PeTTa's own text, so what the operation
    # does is add the atom back and then remove every copy of it.
    assert len(archive) == 0

    # Which makes it a filtered drain today: a second run over the same
    # pattern moves nothing, because nothing is left.
    assert m.fn.migrateAtoms(ledger, archive, S.n(V.x)) == []
    assert len(ledger[S.m(9)]) == 1


from metta import Expression  # noqa: E402  -- read after the claims it serves

#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 14563 inferences, 0.8394x the example's 17349; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 14563 to 14554 (-9), metta_substitute_self/3 probes
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
#: RE-PINNED 2026-09-08, 14554 to 14535 (-19), the evaluation-fuel scope marker
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
#: RE-PINNED 2026-09-08, 14535 to 14910 (+375), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 14910 to 15020 (+110), the module boundary merged with
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
#: RE-PINNED 2026-09-09, 15020 to 15196 (+176), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 15196
