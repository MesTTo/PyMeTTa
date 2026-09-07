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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 119167
