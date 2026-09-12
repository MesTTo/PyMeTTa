"""Purpose: every lib_spaces operation over whole spaces, from Python.

A space is a handle, so the bulk operations take handles and the patterns are
built terms. Each one answers once per atom it touched, and a list of those
answers is the count of work it did.

Guarantees: the same claims as 20-spaces_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/20-spaces_lib.metta; commit=WORKTREE].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import G, S, V, lib


def twin(m):
    """Count, find, copy, move, drain, snapshot, subtract and clear."""
    m += lib.spaces

    ledger = metta.space(S.ledger)
    ledger += S.entry(S.rent, 1200)
    ledger += S.entry(S.food, 300)
    ledger += S.note(G("checked"))

    count, find = m.fn["match-count"], m.fn.find
    copy, move = m.fn["space-copy"], m.fn["move-atoms"]
    drain, snapshot = m.fn["space-drain"], m.fn["space-snapshot"]
    subtract, clear = m.fn["space-subtract"], m.fn["remove-all-atoms"]
    entry = S.entry(V.what, V.amount)

    # match-count folds over a match that answers 1 per solution, so nothing is
    # materialised and a pattern nothing matches counts 0.
    assert count(ledger, entry) == [2]
    assert count(ledger, S.invoice(V.n)) == [0]

    # find is a match reduced to a Bool, and succeedsPredicate asks the same of
    # a Prolog-shaped call.
    assert find(ledger, S.entry(S.rent, V.amount)) == [True]
    assert find(ledger, S.entry(S.car, V.amount)) == [False]
    assert m.fn.succeedsPredicate((ledger, S.entry, S.rent, V.amount)) == [True]

    # space-copy leaves the source alone; a bare variable pattern copies
    # everything, which is how one space merges into another.
    audit = metta.space(S.audit)
    assert sorted(copy(ledger, audit, entry)) == [True, True]
    assert count(audit, entry) == [2]
    assert count(ledger, entry) == [2]
    everything = metta.space(S.everything)
    assert sorted(copy(ledger, everything, V.any)) == [True, True, True]
    assert len(everything) == 3

    # space-snapshot mints the destination itself, so what a space holds now
    # survives later writes to it.
    before = metta.space(snapshot(ledger).one())
    assert len(before) == 3
    ledger += S.entry(S.travel, 90)
    assert len(before) == 3
    assert len(ledger) == 4

    # move-atoms is what migrateAtoms' NAME promises.
    archive = metta.space(S.archive)
    assert move(ledger, archive, S.entry(S.travel, V.amount)) == [True]
    assert [(row.what, row.amount) for row in archive[entry]] == [(S.travel, 90)]
    assert count(ledger, S.entry(S.travel, V.amount)) == [0]

    # migrateAtoms keeps upstream's own equation, which names the source on both
    # sides: it drains, and the destination stays empty. The behaviour rather
    # than the name is what a program relies on.
    nowhere = metta.space(S.nowhere)
    assert [tuple(answer) for answer in m.fn.migrateAtoms(
        ledger, nowhere, S.entry(S.food, V.amount)
    )] == [(True, True)]
    assert list(nowhere) == []
    assert count(ledger, S.entry(S.food, V.amount)) == [0]

    # space-drain answers the atoms it removed.
    assert list(drain(ledger, S.note(V.text))) == [S.note(G("checked"))]
    assert list(ledger) == [S.entry(S.rent, 1200)]

    # space-subtract removes every atom another space holds; an atom the space
    # does not hold answers the removal's ordinary verdict.
    assert sorted(subtract(everything, audit)) == [True, True]
    assert list(everything) == [S.note(G("checked"))]
    assert sorted(subtract(everything, audit)) == [True, True]

    # remove-all-atoms clears a space. Its own body is a collapse over every
    # atom's removal, so one call answers one expression of verdicts.
    assert [tuple(answer) for answer in clear(everything)] == [(True,)]
    assert list(everything) == []
    assert [tuple(answer) for answer in clear(everything)] == [()]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 27 claims cover all nine lib_spaces heads; the
#: example pays 45,668 inferences for the same work
#: [measured 2026-09-12: 43720 inferences, minimum of three serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --measure
#: --rounds 3 examples/ch08-data/08-03-the-shipped-libraries/20-spaces_lib.metta;
#: fixture=lib_spaces at its functional commit, artifacts purged before the run;
#: commit=WORKTREE].
BUDGET = 43720
