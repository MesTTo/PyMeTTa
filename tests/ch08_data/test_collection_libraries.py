"""Purpose: compare MeTTa collection compositions with independent Python models.

Guarantees: itertools, arithmetic, slicing, stable sorting and set algebra cover
literal occurrences, callback alternatives and variable argument counts.
[tested: test_collection_libraries.py; commit=6471fbad35eced5ed6440ebf2c25a053b20221f3].
"""

from itertools import accumulate, combinations, permutations, product
from math import comb, factorial, perm

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def collections(metta):
    """Import the public collection libraries and their common basis."""
    metta += lib.pairs
    metta += lib.sets
    return metta


VALUES = st.one_of(st.integers(-3, 3), st.text(alphabet="aπ🙂\0", max_size=3).map(G),
                   st.sampled_from([S.a, S.b, (), (S["+"], 1, 2), (S.Error, S.a, S.b)]))


@settings(max_examples=100, deadline=None)
@given(st.lists(VALUES, max_size=5), st.integers(0, 6))
def test_collection_choices(collections, values, count):
    """Each occurrence occupies a distinct position, including duplicate values."""
    data = S.quote(tuple(values))
    assert collections.fn.permutations(data) == list(permutations(values))
    assert collections.fn.chooseK(data, count) == list(combinations(values, count))
    assert collections.fn.chooseKl(data, count) == [tuple(combinations(values, count))]
    pairs = [(values[i], values[j]) for j in range(len(values)) for i in range(j)]
    assert collections.fn.choose2l(data) == [tuple(pairs)]
    subsets = [tuple(value for value, take in zip(values, reversed(bits), strict=True) if take)
               for bits in product((True, False), repeat=len(values))]
    assert collections.fn.subsets(data) == subsets


@settings(max_examples=100, deadline=None)
@given(st.lists(st.lists(VALUES, max_size=3), max_size=3),
       st.lists(VALUES, max_size=3), st.integers(0, 4))
def test_collection_products(collections, populations, values, count):
    """Products include one empty tuple and stop when any population is empty."""
    pools = tuple(tuple(pool) for pool in populations)
    assert collections.fn.tuples(S.quote(pools)) == list(product(*populations))
    assert collections.fn.cartesian_power(S.quote(tuple(values)), count) == list(
        product(values, repeat=count))


@settings(max_examples=100, deadline=None)
@given(st.integers(0, 100), st.integers(-2, 102))
def test_collection_exact_counts(collections, size, count):
    """The count formulas retain integers beyond floating precision."""
    assert collections.fn.factorial(size) == [factorial(size)]
    choices = comb(size, count) if 0 <= count <= size else 0
    arrangements = perm(size, count) if 0 <= count <= size else 0
    assert collections.fn.binomial(size, count) == [choices]
    assert collections.fn.permutation_count(size, count) == [arrangements]


@settings(max_examples=100, deadline=None)
@given(st.lists(VALUES, max_size=12), st.lists(VALUES, max_size=12),
       st.integers(1, 6), st.integers(0, 20))
def test_collection_slices(collections, left, right, width, dropped):
    """Slices agree with Python offsets, keeping runnable expressions literal."""
    data, other = S.quote(tuple(left)), S.quote(tuple(right))
    paired = tuple(zip(left, right, strict=False))
    assert collections.fn.zip(data, other) == [paired]
    sides = tuple(tuple(side) for side in zip(*paired, strict=True)) if paired else ((), ())
    assert collections.fn.unzip(S.quote(paired)) == [sides]
    assert collections.fn.drop(data, dropped) == [tuple(left[dropped:])]
    assert collections.fn.chunk(data, width) == [
        tuple(tuple(left[i:i + width]) for i in range(0, len(left), width))]
    assert collections.fn.window(data, width) == [
        tuple(tuple(left[i:i + width]) for i in range(len(left) - width + 1))]


@settings(max_examples=100, deadline=None)
@given(st.lists(st.tuples(st.integers(-3, 3), st.integers(-5, 5)), max_size=12),
       st.integers(-4, 4))
def test_collection_relations(collections, rows, key):
    """Stable sorting and a Python multimap model every relation projection."""
    data = S.quote(tuple(rows))
    assert collections.fn.pairs_keys(data) == [tuple(k for k, _ in rows)]
    assert collections.fn.pairs_values(data) == [tuple(v for _, v in rows)]
    assert collections.fn.pairs_swap(data) == [tuple((v, k) for k, v in rows)]
    by_key = tuple(sorted(rows, key=lambda row: row[0]))
    assert collections.fn.pairs_sort_by_key(data) == [by_key]
    assert collections.fn.pairs_sort_by_value(data) == [tuple(sorted(rows, key=lambda row: row[1]))]
    groups = {}
    for k, value in rows:
        groups.setdefault(k, []).append(value)
    expected = tuple((k, tuple(groups[k])) for k in sorted(groups))
    assert collections.fn.pairs_group(data) == [expected]
    assert collections.fn.pairs_ungroup(S.quote(expected)) == [by_key]
    assert collections.fn.pairs_lookup(data, key) == [v for k, v in rows if k == key]


@settings(max_examples=100, deadline=None)
@given(st.lists(st.sets(st.integers(-10, 10), max_size=8), max_size=12))
def test_collection_variadic_sets(collections, sets):
    """Zero, one and many arguments follow ordinary finite set algebra."""
    inputs = [S.quote(tuple(sorted(values))) for values in sets]
    union = tuple(sorted(set().union(*sets)))
    assert collections.fn.set_union(*inputs) == [union]
    if sets:
        common = tuple(sorted(sets[0].intersection(*sets[1:])))
        assert collections.fn.set_intersection(*inputs) == [common]
    else:
        with pytest.raises(MettaError):
            collections.fn.set_intersection().one()
    if len(sets) >= 2:
        left, right = sets[:2]
        assert collections.fn.set_difference(*inputs[:2]) == [tuple(sorted(left - right))]
        assert collections.fn.set_symmetric_difference(*inputs[:2]) == [tuple(sorted(left ^ right))]
        assert collections.fn.set_subset(*inputs[:2]) == [left <= right]
        assert collections.fn.set_disjoint(*inputs[:2]) == [left.isdisjoint(right)]


@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(-3, 3), max_size=4), st.integers(-5, 5), st.integers(0, 4))
def test_collection_callback_paths(collections, values, seed, count):
    """A callback choice contributes one independent dimension to each path."""
    add = S["|->"]((V.a, V.b), S.superpose((V.a + V.b, V.a + V.b + 1)))
    histories = [tuple(accumulate((v + d for v, d in zip(values, deltas, strict=True)),
                                 initial=seed))
                 for deltas in product((0, 1), repeat=len(values))]
    assert collections.fn.scan(add, seed, tuple(values)) == histories
    step = S["|->"]((V.n,), S["if"](S.lt(V.n, count),
                                   S.superpose(((V.n, V.n + 1), (V.n + 10, V.n + 1))),
                                   S.empty()))
    assert collections.fn.unfold(step, 0) == list(product(*[(n, n + 10) for n in range(count)]))
    key = S["|->"]((V.x,), S.superpose((S["%"](V.x, 2), S["%"](V.x, 2) + 2)))
    expected = []
    for keys in product(*[(value % 2, value % 2 + 2) for value in values]):
        groups = {}
        for k, value in zip(keys, values, strict=True):
            groups.setdefault(k, []).append(value)
        expected.append(tuple((k, tuple(members)) for k, members in groups.items()))
    assert collections.fn.group_by(key, tuple(values)) == expected


def test_collection_foreign_identity_and_error_data(collections):
    """Native object identity survives literal collection and function boundaries."""
    value = object()
    assert collections.fn.pairs_lookup(((S.key, value),), S.key).one() is value
    identity = S["|->"]((V.x,), S.quote(V.x))
    assert collections.fn.apply_to(identity, (value,)).one() is value
    assert collections.fn.pipe((identity,), value).one() is value
    error_data = (S.Error, S.a, S.b)
    assert collections.fn.set_union(S.quote(error_data), ()) == [error_data]
    assert collections.fn.set_intersection(S.quote(error_data)) == [error_data]


@pytest.mark.parametrize("call", [
    S.factorial(1.0), S.chooseK((S.a,), -1), S.cartesian_power((S.a,), 1.0),
    S.tuples(S.quote(((), S.invalid))), S.unzip((1,)), S.chunk((1,), 0),
    S.window((1,), 0), S.drop((1,), -1), S.pairs_ungroup(((S.a, 1),)),
    S.set_union((2, 1)), S.set_intersection((1, 1)),
    S.set_intersection((1,), (2, 1)),
])
def test_collection_invalid_domains(collections, call):
    """Malformed shapes and invalid counts raise through the public Python door."""
    with pytest.raises(MettaError):
        collections.eval(call)
