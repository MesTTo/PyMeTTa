"""Purpose: verify descriptive statistics against independent exact oracles.

Guarantees: generated observations retain exact moments, nearest roots and
quantile interpolation; nominal modes preserve occurrence order and identity.
[tested: test_statistics_exact_reductions, test_statistics_paired_reductions,
test_statistics_quantiles_and_ranks; commit=WORKTREE].
Owns resources: the shared engine fixture owns the imported library; generated
numeric terms and reference calculations acquire no external resources.
"""

import math
import statistics
from collections import Counter
from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import FALSE, TRUE, G, S, lib, library
from metta._errors.errors import MettaError

from .test_vector_lib import assert_nearest_root, bits, nearest

FINITE = st.one_of(st.integers(-(1 << 256), 1 << 256),
                   st.floats(allow_nan=False, allow_infinity=False))
DATA = st.lists(FINITE, min_size=1, max_size=10)
PAIRS = st.lists(st.tuples(FINITE, FINITE), min_size=2, max_size=10)


@pytest.fixture(scope="module")
def stats(metta):
    """Load sample and finite-law equations with their shared numeric providers."""
    metta += lib.statistics
    return metta


def assert_numeric(actual, expected, data):
    """Check both value and numeric species using the observation type rule."""
    if any(isinstance(value, float) for value in data):
        assert type(actual) is float
        assert bits(actual) == bits(nearest(expected))
    else:
        assert type(actual) in (int, Fraction)
        assert actual == expected


@settings(max_examples=180)
@example([1.0e308, 1, -1.0e308])
@example([-1.0e308, 1.0e308])
@example([-1.0e-300, 1.0e-300])
@example([-(1 << 3000), 1 << 3000])
@given(DATA)
def test_statistics_exact_reductions(stats, data):
    """Fraction statistics and squared midpoint intervals check every reduction."""
    exact = [Fraction(value) for value in data]
    fn = stats.fn
    assert_numeric(fn.stats_sum(tuple(data)).one(), sum(exact), data)
    assert_numeric(fn.stats_mean(tuple(data)).one(), statistics.mean(exact), data)
    assert_numeric(fn.stats_median(tuple(data)).one(), statistics.median(exact), data)
    for ddof in range(len(data)):
        # The oracle centers each observation; covariance uses exact raw
        # moments, so cancellation bugs affect different paths.
        mean = statistics.mean(exact)
        variance = sum((value - mean) ** 2 for value in exact) / (len(data) - ddof)
        assert_numeric(fn.stats_variance(tuple(data), ddof).one(), variance, data)
        assert_nearest_root(variance, fn.stats_stdev(tuple(data), ddof).one())
    if min(data) >= 0:
        harmonic = 0 if 0 in exact else len(data) / sum(1 / value for value in exact)
        assert_numeric(fn.stats_harmonic_mean(tuple(data)).one(), harmonic, data)


@settings(max_examples=160)
@example([(-1.0e308, 1.0e308), (1.0e308, -1.0e308)])
@example([(0, 1), (1, 5), (2, 9)])
@example([(1 << 3000, 3), (-(1 << 3000), -3)])
@given(PAIRS)
def test_statistics_paired_reductions(stats, pairs):
    """Centered Fraction products check paired moments and both fit models."""
    left, right = tuple(x for x, _ in pairs), tuple(y for _, y in pairs)
    a, b = [Fraction(x) for x in left], [Fraction(y) for y in right]
    mx, my = statistics.mean(a), statistics.mean(b)
    centered_a, centered_b = [x - mx for x in a], [y - my for y in b]
    xx, yy = sum(x * x for x in centered_a), sum(y * y for y in centered_b)
    xy = sum(x * y for x, y in zip(centered_a, centered_b, strict=True))
    fn = stats.fn
    for ddof in (0, 1):
        covariance = xy / (len(pairs) - ddof)
        assert_numeric(fn.stats_covariance(left, right, ddof).one(), covariance, left + right)
    if xx and yy:
        correlation = fn.stats_correlation(left, right).one()
        assert_nearest_root(xy**2 / (xx * yy), abs(correlation))
        assert (math.copysign(1.0, correlation) < 0) == (xy < 0)
    if xx:
        fit = fn.stats_regression(left, right, FALSE).one()
        slope = xy / xx
        assert fit[0] == S.linear_fit
        assert_numeric(fit[1].value, slope, left + right)
        assert_numeric(fit[2].value, my - slope * mx, left + right)
    raw_xx = sum(x * x for x in a)
    if raw_xx:
        fit = fn.stats_regression(left, right, TRUE).one()
        slope = sum(x * y for x, y in zip(a, b, strict=True)) / raw_xx
        assert_numeric(fit[1].value, slope, left + right)
        assert_numeric(fit[2].value, Fraction(0), left + right)


@settings(max_examples=160)
@given(DATA, st.integers(1, 25))
def test_statistics_quantiles_and_ranks(stats, data, partitions):
    """CPython Fraction quantiles and independent order counts supply the oracle."""
    exact = [Fraction(value) for value in data]
    fn = stats.fn
    for method in ("inclusive", "exclusive"):
        expected = (exact * (partitions - 1) if len(data) == 1
                    else statistics.quantiles(exact, n=partitions, method=method))
        actual = fn.stats_quantiles(tuple(data), partitions, S[method]).one()
        assert len(actual) == len(expected)
        for value, reference in zip(actual, expected, strict=True):
            assert_numeric(value.value, reference, data)
    ranks = fn.stats_ranks(tuple(data)).one()
    for value, rank in zip(exact, ranks, strict=True):
        lower = sum(other < value for other in exact)
        tied = sum(other == value for other in exact)
        assert rank.value == lower + Fraction(tied + 1, 2)


@settings(max_examples=160)
@example([0.0, 0.0])
@example([1.0e308, 1.0e308])
@example([5.0e-324, 5.0e-324])
@given(st.lists(st.floats(min_value=0, allow_nan=False, allow_infinity=False), min_size=1, max_size=10))
def test_statistics_geometric_mean_precision_and_bounds(stats, data):
    """Decimal logarithms check the approximation across the binary64 range."""
    from decimal import Decimal, localcontext

    with localcontext() as context:
        context.prec = 80
        expected = (0.0 if 0 in data else
                    float((sum(Decimal(value).ln() for value in data) / len(data)).exp()))
    actual = stats.fn.stats_geometric_mean(tuple(data)).one()
    assert min(data) <= actual <= max(data)
    # Absolute tolerance is one final subnormal quantum; relative tolerance
    # covers native log/exp rounding, which is not a correctly-rounded claim.
    assert math.isclose(actual, expected, rel_tol=8e-16, abs_tol=5e-324)


@settings(max_examples=160)
@given(st.lists(st.text(alphabet="abc", max_size=4), min_size=1, max_size=25))
def test_statistics_modes_keep_first_occurrence_order(stats, data):
    """Counter multiplicities check all tied modes through held string values."""
    counts = Counter(data)
    most = max(counts.values())
    expected = [G(value) for value, count in counts.items() if count == most]
    assert list(stats.fn.stats_mode(tuple(G(value) for value in data))) == expected


@pytest.mark.parametrize("value", [G("bad"), TRUE, S.untyped_observation, (1, 2), (), math.inf, math.nan])
def test_statistics_rejects_every_nonfinite_or_nonnumeric_observation(stats, value):
    """Typed Error data and native refusals both stop the sample reduction."""
    for function in (stats.fn.stats_sum, stats.fn.stats_mean, stats.fn.stats_ranks):
        with pytest.raises(MettaError):
            function((1, value)).one()


def test_statistics_card_and_shared_root_visibility():
    """One domain owns sample recipes and finite laws; Math owns root rounding."""
    card = library.card("lib_statistics")
    assert len(card.heads) == len(card.documented) == 29
    assert any(path.name == "37-statistics_lib.metta" for path in card.examples)
    assert any(path.name == "12-distribution.metta" for path in card.examples)
    assert "lib_distribution" not in library.roster()
    assert any(row.name == "math-sqrt" for row in library.rows("lib_math"))
    vectors = library.card("lib_vector")
    assert len(vectors.heads) == len(vectors.documented) == 13
