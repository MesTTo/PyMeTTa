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
BUDGET = 14563
