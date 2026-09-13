"""Purpose: compare composed testing domains and assertions with Python models.

Guarantees: products agree with itertools and bag verdicts agree with Counter;
literal foreign values retain the caller's identity through ordinary iteration.
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
    """Import the generator bundle through the public library door."""
    metta += lib.testing
    return metta


VALUES = st.one_of(st.integers(min_value=-20, max_value=20),
                   st.text(alphabet="aπ🙂\0", max_size=4).map(G),
                   st.sampled_from([S.alpha, S.beta, (), (S["+"], 1, 2)]))


@settings(max_examples=80, deadline=None)
@given(st.lists(VALUES, max_size=3), st.integers(0, 4), st.integers(0, 4))
def test_testing_products(testing, values, minimum, maximum):
    """Population and length vary independently, retaining literal occurrences."""
    expected = [items for size in range(minimum, maximum + 1)
                for items in product(values, repeat=size)]
    assert testing.fn.cartesian_power(
        S.quote(tuple(values)), S.range(minimum, maximum + 1)) == expected


@settings(max_examples=80, deadline=None)
@given(st.lists(st.integers(-2, 2), max_size=8),
       st.lists(st.integers(-2, 2), max_size=8), st.integers(0, 4))
def test_testing_quantified_bags(testing, actual, expected, count):
    """A bag assertion compares multiplicity and forall handles empty domains."""
    generator = S.range(1, count + 1)
    answers = S.superpose(tuple(actual))
    assertion = S["|->"]((V.x,), S.assertEqualToResult(answers, tuple(expected)))
    equal = Counter(actual) == Counter(expected)
    same_bag = S["=="](S.sort_atom(S.collapse(answers)), tuple(sorted(expected)))
    selected = S.let(V.x, generator, S["if"](same_bag, V.x, S.empty()))
    assert testing.fn.once(selected) == ([1] if equal and count else [])
    if equal or count == 0:
        assert testing.fn.forall(generator, assertion) == [True]
    else:
        with pytest.raises(AssertionFailure) as raised:
            testing.fn.forall(generator, assertion).one()
        assert Counter(raised.value.missing) == Counter(expected) - Counter(actual)
        assert Counter(raised.value.excess) == Counter(actual) - Counter(expected)


def test_testing_foreign_values(testing):
    """Literal iteration and commitment return an opaque value without copying it."""
    value = object()
    generator = S.index_atom(S.quote((value,)), 0)
    assertion = S["|->"]((V.x,), S.assertEqualToResult(S.quote(V.x), (value,)))
    assert testing.fn.forall(generator, assertion) == [True]
    assert testing.fn.once(generator).one() is value
