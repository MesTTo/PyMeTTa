"""Purpose: check immutable collection equations with independent Python models.

Guarantees: generated edit sequences, stable queue order, multiplicity and
immutable inputs are compared through public MeTTa calls; identity and quoted
syntax remain data [tested: test_datastructures_lib.py; commit=WORKTREE].
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import S, V, lib
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def collections(metta):
    """Import the public collection equations."""
    metta += lib.datastructures
    return metta


@settings(max_examples=70, deadline=None)
@given(st.lists(st.tuples(st.booleans(), st.integers(-5, 5), st.integers()), max_size=30))
def test_map_edit_sequences(collections, edits):
    """A Python dict predicts every version, including replacement and absence."""
    model = {}
    current = collections.fn.map_empty().one()
    for insert, key, value in edits:
        previous = current
        previous_rows = tuple(sorted(model.items()))
        if insert:
            current = collections.fn.map_put(current, key, value).one()
            model[key] = value
        else:
            current = collections.fn.map_remove(current, key).one()
            model.pop(key, None)
        expected = tuple(sorted(model.items()))
        assert collections.fn.map_pairs(previous) == [previous_rows]
        assert collections.fn.map_pairs(current) == [expected]
        assert collections.fn.map_size(current) == [len(model)]
        assert collections.fn.map_keys(current) == [tuple(sorted(model))]
        assert collections.fn.map_values(current) == [tuple(v for _, v in expected)]
        assert collections.fn.map_has(current, key) == [key in model]
        assert collections.fn.map_get(current, key) == ([model[key]] if key in model else [])
        assert collections.fn.map_get_or(current, key, S.absent) == [model.get(key, S.absent)]
        assert collections.fn.map_min(current) == ([expected[0]] if expected else [])
        assert collections.fn.map_max(current) == ([expected[-1]] if expected else [])


ROWS = st.lists(st.tuples(st.integers(-3, 3), st.integers(0, 5)), max_size=25)


@settings(max_examples=70, deadline=None)
@given(ROWS, ROWS, st.integers(-3, 3), st.integers(0, 5))
def test_priority_queue_model(collections, left, right, priority, value):
    """Stable sorting predicts ties, merged occurrences and successive pops."""
    first = collections.fn.pq_from_pairs(tuple(left)).one()
    second = collections.fn.pq_from_pairs(tuple(right)).one()
    queue = collections.fn.pq_merge(first, second).one()
    expected = sorted(left + right, key=lambda pair: pair[0])
    assert collections.fn.pq_pairs(queue) == [tuple(expected)]
    assert collections.fn.pq_pairs(first) == [tuple(sorted(left, key=lambda pair: pair[0]))]
    assert collections.fn.pq_pairs(second) == [tuple(sorted(right, key=lambda pair: pair[0]))]
    inserted = collections.fn.pq_insert(queue, priority, value).one()
    assert collections.fn.pq_pairs(inserted) == [
        tuple(sorted([*expected, (priority, value)], key=lambda pair: pair[0])),
    ]
    removed = collections.fn.pq_remove(queue, priority, value)
    if (priority, value) in expected:
        without = expected.copy()
        without.remove((priority, value))
        assert collections.fn.pq_pairs(removed.one()) == [tuple(without)]
    else:
        assert removed == []
    for index, entry in enumerate(expected):
        assert collections.fn.pq_size(queue) == [len(expected) - index]
        assert collections.fn.pq_min(queue) == [entry]
        actual_priority, actual_value, queue = collections.fn.pq_pop(queue).one()
        assert (actual_priority, actual_value) == entry
    assert collections.fn.pq_size(queue) == [0]
    assert collections.fn.pq_min(queue) == []
    assert collections.fn.pq_pop(queue) == []


@pytest.mark.parametrize("call", [
    S.map_from_pairs(S.quote(((S.a, 1), (S.a, 2)))),
    S.map_from_pairs(S.quote(((V.x, 1), (V.x, 2)))),
    S.map_from_pairs(S.quote((V.pair,))),
    S.pq_from_pairs(S.quote((V.pair,))),
    S.map_from_pairs(S.quote(((S.a,),))),
    S.pq_from_pairs(S.quote(((1, S.a, S.b),))),
    S.map_size(S.PriorityQueue(())),
    S.pq_size(S.SortedMap(())),
    S.map_size(S.SortedMap(((S.a, 1), (S.a, 2)))),
    S.map_size(S.SortedMap(((S.b, 1), (S.a, 2)))),
    S.pq_size(S.PriorityQueue(((2, S.a), (1, S.b)))),
    S.map_get(42, S.a),
    S.pq_min(42),
])
def test_collection_refusals(collections, call):
    """Malformed relations and wrong kinds fail through the public door."""
    with pytest.raises(MettaError):
        collections.eval(call)


def test_literal_values_and_numeric_key_kinds(collections):
    """Runnable values stay literal, and integral floats are distinct keys."""
    expression = S["+"](1, 2)
    error = S.Error(S.data, S.code)
    mapping = collections.fn.map_from_pairs(S.quote(((expression, error),))).one()
    assert collections.fn.map_get(S.quote(mapping), S.quote(expression)) == [error]
    assert collections.fn.map_get_or(S.quote(mapping), S.absent, S.quote(expression)) == [expression]
    queue = collections.fn.pq_from_pairs(S.quote(((expression, error),))).one()
    priority, value, rest = collections.fn.pq_pop(S.quote(queue)).one()
    assert priority == expression and value == error
    assert collections.fn.pq_pairs(rest) == [()]
    numeric = collections.fn.map_from_pairs(((1, S.integer), (1.0, S.float))).one()
    assert collections.fn.map_size(numeric) == [2]
    assert collections.fn.map_get(numeric, 1) == [S.integer]
    assert collections.fn.map_get(numeric, 1.0) == [S.float]


def test_sharing_and_reflection(collections):
    """Identity tests execute in one MeTTa scope; matching recovers the recipe."""
    shared = ((V.x, S.a), (V.y, S.b))
    assert collections.eval(S.let(
        V.mapping, S.map_from_pairs(S.quote(shared)),
        S["=="](S.map_keys(V.mapping), S.quote((V.x, V.y))),
    )) == [True]
    assert collections.eval(S.let(
        V.mapping, S.map_from_pairs(S.quote(shared)), S.map_has(V.mapping, V.fresh),
    )) == [False]
    row = collections.match(S["="](S.map_remove(V.mapping, V.key), V.body)).one()
    recipe = collections.eval(S["|->"]((row.mapping, row.key), row.body))[0]
    mapping = collections.fn.map_from_pairs(((S.a, 1), (S.b, 2))).one()
    changed = collections.eval((recipe, mapping, S.a))[0]
    assert collections.fn.map_pairs(changed) == [((S.b, 2),)]


@pytest.mark.parametrize("count", [0, 1, 2, 3, 11, 31])
def test_variadic_merge(collections, count):
    """A runtime argument sequence has no fixed merge arity."""
    queue = collections.fn.pq_from_pairs(((1, S.a),)).one()
    answer = collections.fn.pq_merge(*([queue] * count)).one()
    assert collections.fn.pq_pairs(answer) == [((1, S.a),) * count]
