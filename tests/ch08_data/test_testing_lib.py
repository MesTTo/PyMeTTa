"""Purpose: compare finite native generators and quantified bags with Python models.

Guarantees: generated products agree with itertools and quantified verdicts
agree with Counter; literal foreign values keep the caller's identity.
[tested: test_testing_products, test_testing_quantified_bags,
test_testing_foreign_values; commit=WORKTREE].
"""

from collections import Counter
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib
from metta._errors.errors import AssertionFailure


@pytest.fixture(scope="module")
def testing(metta):
    """Use the generated library face through the public Python import door."""
    metta += lib.testing
    return metta


VALUES = st.one_of(st.integers(min_value=-20, max_value=20),
                   st.text(alphabet="aπ🙂\0", max_size=4).map(G),
                   st.sampled_from([S.alpha, S.beta, (), (S["+"], 1, 2)]))


@settings(max_examples=80, deadline=None)
@given(st.lists(VALUES, max_size=3), st.integers(0, 4), st.integers(0, 4))
def test_testing_products(testing, values, minimum, maximum):
    """Every product retains order, duplicates, empty cases and literal terms."""
    expected = [items for size in range(minimum, maximum + 1)
                for items in product(values, repeat=size)]
    assert testing.fn.test_lists(S.test_choices(tuple(values)), minimum, maximum) == expected


@settings(max_examples=80, deadline=None)
@given(st.lists(st.integers(-2, 2), max_size=8),
       st.lists(st.integers(-2, 2), max_size=8), st.integers(0, 4))
def test_testing_quantified_bags(testing, actual, expected, count):
    """Multiplicity decides equality; empty domains report zero and no witness."""
    generator = S.test_integers(1, count)
    function = S["|->"]((V.x,), S.superpose(tuple(actual)))
    equal = Counter(actual) == Counter(expected)
    assert testing.fn.test_witness(generator, function, tuple(expected)) == ([1] if equal and count else [])
    if equal or count == 0:
        assert testing.fn.test_forall(generator, function, tuple(expected)) == [count]
    else:
        with pytest.raises(AssertionFailure) as raised:
            testing.fn.test_forall(generator, function, tuple(expected)).one()
        assert Counter(raised.value.missing) == Counter(expected) - Counter(actual)
        assert Counter(raised.value.excess) == Counter(actual) - Counter(expected)


def test_testing_foreign_values(testing):
    """An opaque input is quoted and returned, with no new owner or conversion."""
    value = object()
    generator = S.test_choices((value,))
    identity = S["|->"]((V.x,), V.x)
    assert testing.fn.test_forall(generator, identity, (value,)) == [1]
    assert testing.fn.test_witness(generator, identity, (value,)).one() is value
