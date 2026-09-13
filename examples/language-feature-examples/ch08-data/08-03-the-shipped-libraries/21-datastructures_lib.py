"""Purpose: the sorted map and the priority queue from Python.

Both are VALUES, so each operation answers a new one and the Python name holds
whichever version it was given. A pair is a two-element tuple and a map or a
queue is whatever the library answered, passed straight back.

Guarantees: the same claims as 21-datastructures_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/21-datastructures_lib.metta; commit=9c9e60542491416e2c5e431a2672bb20f04264fa].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """A sorted map, a priority queue, the functional queue and a finger tree."""
    m += lib.datastructures

    empty_map, put, remove = m.fn["map-empty"], m.fn["map-put"], m.fn["map-remove"]
    get, get_or, has = m.fn["map-get"], m.fn["map-get-or"], m.fn["map-has"]
    keys, values, pairs = m.fn["map-keys"], m.fn["map-values"], m.fn["map-pairs"]
    from_pairs, size = m.fn["map-from-pairs"], m.fn["map-size"]
    smallest, largest = m.fn["map-min"], m.fn["map-max"]

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    def rows(answers):
        """One answer's expression of pairs, as a list of tuples."""
        return [tuple(pair) for pair in answers.one()]

    # Keys compare in the standard order of terms, so the pairs come back sorted
    # however they went in.
    prices = from_pairs(((S.pear, 5), (S.apple, 3), (S.plum, 7))).one()
    assert size(prices) == [3]
    assert list(keys(prices).one()) == [S.apple, S.pear, S.plum]
    assert list(values(prices).one()) == [3, 5, 7]
    assert rows(pairs(prices)) == [(S.apple, 3), (S.pear, 5), (S.plum, 7)]

    # A lookup that finds nothing has NO answer; get-or takes the answer to give.
    assert get(prices, S.pear) == [5]
    assert get(prices, S.durian) == []
    assert get_or(prices, S.durian, 0) == [0]
    assert has(prices, S.apple) == [True]
    assert has(prices, S.durian) == [False]
    assert tuple(smallest(prices).one()) == (S.apple, 3)
    assert tuple(largest(prices).one()) == (S.plum, 7)

    # A put answers a NEW map and leaves the old one alone.
    raised = put(prices, S.pear, 6).one()
    assert rows(pairs(raised)) == [(S.apple, 3), (S.pear, 6), (S.plum, 7)]
    assert rows(pairs(prices)) == [(S.apple, 3), (S.pear, 5), (S.plum, 7)]
    assert rows(pairs(remove(prices, S.pear).one())) == [(S.apple, 3), (S.plum, 7)]
    assert rows(pairs(remove(prices, S.durian).one())) == [
        (S.apple, 3), (S.pear, 5), (S.plum, 7),
    ]
    assert size(empty_map().one()) == [0]
    assert rows(pairs(put(empty_map().one(), S.k, S.v).one())) == [(S.k, S.v)]

    # A key holds one value, so two values for one key is refused where it is
    # written rather than silently keeping the last.
    assert refused(S.map_from_pairs(((S.k, 1), (S.k, 2))))
    assert refused(S.map_get(42, S.k))

    # Priority order retains every inserted occurrence.
    empty_queue, insert = m.fn["pq-empty"], m.fn["pq-insert"]
    queue_min, pop, queue_size = m.fn["pq-min"], m.fn["pq-pop"], m.fn["pq-size"]
    queue_pairs, queue_from = m.fn["pq-pairs"], m.fn["pq-from-pairs"]
    merge, cancel = m.fn["pq-merge"], m.fn["pq-remove"]

    work = queue_from(((3, S.sweep), (1, S.wake), (2, S.boil))).one()
    assert queue_size(work) == [3]
    assert tuple(queue_min(work).one()) == (1, S.wake)
    assert rows(queue_pairs(work)) == [(1, S.wake), (2, S.boil), (3, S.sweep)]

    # Pop decomposes the first entry and remaining queue together.
    priority, value, rest = pop(work).one()
    assert (priority, value) == (1, S.wake)
    assert queue_size(rest) == [2]
    assert rows(queue_pairs(rest)) == [(2, S.boil), (3, S.sweep)]
    assert queue_size(work) == [3]

    # Repeated priorities are kept; merging is one operation over both queues,
    # and removing a named entry cancels it.
    assert queue_size(queue_from(((1, S.a), (1, S.b))).one()) == [2]
    assert rows(queue_pairs(insert(work, 0, S.rise).one())) == [
        (0, S.rise), (1, S.wake), (2, S.boil), (3, S.sweep),
    ]
    assert rows(queue_pairs(merge(work, queue_from(((0, S.rise),)).one()).one())) == [
        (0, S.rise), (1, S.wake), (2, S.boil), (3, S.sweep),
    ]
    assert rows(queue_pairs(cancel(work, 2, S.boil).one())) == [(1, S.wake), (3, S.sweep)]
    assert cancel(work, 2, S.absent) == []
    assert queue_size(empty_queue().one()) == [0]
    assert queue_min(empty_queue().one()) == []
    assert pop(empty_queue().one()) == []
    assert refused(S.pq_size(42))

    # The functional queue that was here before: two lists, amortized constant
    # time at both ends.
    enqueue, dequeue = m.fn.enqueue, m.fn.dequeue
    one = enqueue(1, m.fn["empty-queue"]().one()).one()
    two = enqueue(2, one).one()
    # `cons` builds the expression, so the stored queue reads (queue (2 1) () 2).
    assert two == S.queue((2, 1), (), 2)
    assert dequeue(1, two) == [S.queue((), (2,), 1)]

    # And the finger tree, which is the deque: both ends in amortized constant
    # time and concatenation in O(log n).
    tree, to_list = m.fn["ft-from-list"], m.fn["ft-to-list"]
    assert list(to_list(tree((1, 2, 3)).one()).one()) == [1, 2, 3]
    assert m.fn["ft-front"](tree((1, 2, 3)).one()) == [1]
    assert m.fn["ft-back"](tree((1, 2, 3)).one()) == [3]
    joined = m.fn["ft-concat"](tree((1, 2)).one(), tree((3, 4)).one()).one()
    assert list(to_list(joined).one()) == [1, 2, 3, 4]
    assert m.fn["ft-is-empty"](m.fn["ft-empty"]().one()) == [True]

    assert prices == S.SortedMap(((S.apple, 3), (S.pear, 5), (S.plum, 7)))
    assert m.fn.pairs_lookup(prices[1], S.pear) == [5]
    assert merge() == [empty_queue().one()]
    assert merge(work) == [work]
    assert queue_size(merge(work, work, work).one()) == [9]
    queues = (work, work)
    assert queue_size(merge(*queues).one()) == [6]
    tied = queue_from(((1, S.a), (1, S.b), (1, S.c))).one()
    assert rows(queue_pairs(tied)) == [(1, S.a), (1, S.b), (1, S.c)]
    tied = insert(queue_from(((1, S.a), (1, S.b))).one(), 1, S.c).one()
    assert rows(queue_pairs(tied)) == [(1, S.a), (1, S.b), (1, S.c)]
    repeated = queue_from(((1, S.a), (1, S.a), (2, S.b))).one()
    assert rows(queue_pairs(cancel(repeated, 1, S.a).one())) == [(1, S.a), (2, S.b)]
    assert refused(S.map_from_pairs(S.quote(((V.x, S.a), (V.x, S.b)))))
    assert refused(S.map_from_pairs(S.quote((V.pair,))))
    shared = S.quote(((V.x, S.a), (V.y, S.b)))
    assert get(S.map_from_pairs(shared), V.x) == [S.a]
    literal = S.map_from_pairs(S.quote(((S["+"](1, 2), S.Error(S.data, S.code)),)))
    assert get(literal, S.quote(S["+"](1, 2))) == [S.Error(S.data, S.code)]
    assert refused(S.map_size(empty_queue().one()))
    assert refused(S.pq_size(empty_map().one()))
    choices = S.superpose((((S.a, 1),), ((S.a, 2),)))
    assert get(S.map_from_pairs(choices), S.a) == [1, 2]
    row = m.match(S["="](S.map_remove(V.map, V.key), V.body)).one()
    recipe = m.eval(S["|->"]((row.map, row.key), row.body))[0]
    assert rows(pairs(m.eval((recipe, prices, S.pear))[0])) == [(S.apple, 3), (S.plum, 7)]
    row = m.match(S["="](S.map_remove(prices, V.key), V.body)).one()
    recipe = m.eval(S["|->"]((row.key,), row.body))[0]
    assert rows(pairs(m.eval((recipe, S.plum))[0])) == [(S.apple, 3), (S.pear, 5)]


#: The native 41-claim fixture was pinned at 240981. The derived fixture adds
#: stable ties, variadic merge, literal values and reflection.
#: [measured: 3062103 inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/21-datastructures_lib.metta;
#: fixture=59 claims, fresh serial processes after engine/lib QLF purge,
#: MeTTa 3172046; commit=9c9e60542491416e2c5e431a2672bb20f04264fa].
#: RE-PINNED 2026-09-14, 3062103 to 3108074 (+45971), Functional applies
#: finished callback arguments through reduce; Statistics derives exact
#: coefficient rows and Combinatorics retires its native probability provider
#: [measured 2026-09-14: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=e1be99ea1c08f70444c1c35cada441e089777906].
BUDGET = 3108074
