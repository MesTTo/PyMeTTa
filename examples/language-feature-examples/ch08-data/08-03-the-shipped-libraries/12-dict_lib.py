"""examples/ch08-data/08-03-the-shipped-libraries/12-dict_lib.metta in Python: a dict IS a space.

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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 95025
