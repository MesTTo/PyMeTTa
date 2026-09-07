"""examples/ch08-data/08-03-the-shipped-libraries/15-fingertree_internals.metta in Python: the 2-3 finger tree from the inside.

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
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 208634
