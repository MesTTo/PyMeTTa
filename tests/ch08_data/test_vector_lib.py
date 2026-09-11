"""Purpose: verify Vector's public arithmetic against independent exact oracles.

Guarantees: generated vectors retain exact finite reductions, nearest floating
rounding, IEEE class/sign behavior and reusable rational results
[tested: test_vector_exact_reductions, test_vector_rational_rounding,
test_vector_ieee_arithmetic, test_vector_rationals_compose; commit=615e8a68dce996a0c05b3ddddc71b80bc598442d].
Owns resources: the shared engine fixture owns the imported library; tests
produce immutable numeric expressions and acquire no external resources.
"""

import decimal
import math
import operator
import struct
import sys
from fractions import Fraction
from itertools import product

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import S, lib, library
from metta._errors.errors import MettaOperationError

FINITE = st.one_of(st.integers(-(1 << 256), 1 << 256),
                   st.floats(allow_nan=False, allow_infinity=False))
PAIRS = st.lists(st.tuples(FINITE, FINITE), max_size=10)


@pytest.fixture(scope="module")
def vectors(metta):
    """Import the actual shipped native face for all generated cases."""
    metta += lib.vector
    return metta


def bits(value):
    """Read the binary64 payload, including its zero sign."""
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def nearest(value):
    """Use Python's exact integer-ratio conversion with IEEE overflow results."""
    try:
        return float(value)
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def assert_nearest_root(value, actual):
    """Check exact squared midpoint bounds independently of the root algorithm."""
    assert actual >= 0.0 and bits(actual) >> 63 == 0
    if actual == 0.0:
        assert value <= Fraction(1, 1 << 1075) ** 2
        return
    overflow_midpoint = (Fraction(sys.float_info.max) + (1 << 1024)) / 2
    if math.isinf(actual):
        assert value >= overflow_midpoint**2
        return
    center = Fraction(actual)
    before = Fraction(math.nextafter(actual, -math.inf))
    following = math.nextafter(actual, math.inf)
    after = Fraction(following) if math.isfinite(following) else Fraction(1 << 1024)
    low, high = ((center + before) / 2) ** 2, ((center + after) / 2) ** 2
    assert low <= value <= high
    assert bits(actual) & 1 == 0 or value not in (low, high)


@settings(max_examples=180)
@example([(2.0**54, 1.0), (1.0, 1.0), (-(2.0**54), 1.0)])
@example([(1 + 2.0**-27, 1 - 2.0**-27), (1.0, -1.0)])
@example([(2.0**1000, 2.0**1000), (2.0**1000, -(2.0**1000))])
@example([(2.0**-1074, 0.5), (2.0**-1074, 0.5)])
@example([((1 << 3000), 1), (1, -(1 << 3000))])
@given(PAIRS)
def test_vector_exact_reductions(vectors, pairs):
    """Fraction sums and squared intervals check dot, norm, distance and direction."""
    left = tuple(a for a, _ in pairs)
    right = tuple(b for _, b in pairs)
    a = [Fraction(value) for value in left]
    b = [Fraction(value) for value in right]
    dot = sum((x * y for x, y in zip(a, b, strict=True)), Fraction(0))
    a2 = sum((x * x for x in a), Fraction(0))
    b2 = sum((y * y for y in b), Fraction(0))
    distance2 = sum(((x - y) ** 2 for x, y in zip(a, b, strict=True)), Fraction(0))
    fn = vectors.fn
    assert bits(fn.dot(left, right).one()) == bits(nearest(dot))
    assert bits(fn.cosine_of_normalized(left, right).one()) == bits(nearest(dot))
    assert_nearest_root(a2, fn.norm(left).one())
    assert_nearest_root(b2, fn.norm(right).one())
    assert_nearest_root(distance2, fn.vector_distance(left, right).one())
    angle = fn.cosine(left, right).one()
    if a2 and b2:
        assert_nearest_root(dot**2 / (a2 * b2), abs(angle))
        assert (math.copysign(1.0, angle) < 0) == (dot < 0)
    else:
        assert math.isnan(angle)
    unit = fn.vector_normalize(left).one()
    assert len(unit) == len(left)
    for original, exact, actual in zip(left, a, unit, strict=True):
        if a2:
            assert_nearest_root(exact**2 / a2, abs(actual.value))
            sign = math.copysign(1.0, original) if isinstance(original, float) else (-1 if original < 0 else 1)
            assert math.copysign(1.0, actual.value) == sign
        else:
            assert math.isnan(actual.value)


@settings(max_examples=160)
@example((1 << 54) + 1, 1, -1129)
@example(1, 1, -1075)
@example((1 << 54) - 1, 1, 970)
@given(st.integers(1, 1 << 100), st.integers(1, 1 << 100), st.integers(-2600, 2600))
def test_vector_rational_rounding(vectors, numerator, denominator, exponent):
    """Engine-created ratios cross back before positive and negative rounding."""
    value = Fraction(numerator, denominator)
    value = value * (1 << exponent) if exponent >= 0 else value / (1 << -exponent)
    for signed in (value, -value):
        atom = vectors.fn.vector_divide((signed.numerator,), (signed.denominator,)).one()
        assert atom[0].value == signed
        assert bits(vectors.fn.dot(atom, (1,)).one()) == bits(nearest(signed))
        assert_nearest_root(signed**2, vectors.fn.norm(atom).one())


@settings(max_examples=120)
@given(PAIRS)
def test_vector_component_arithmetic(vectors, pairs):
    """Exact operands retain exact results and mixed operands round only once."""
    left = tuple(a for a, _ in pairs)
    right = tuple(b for _, b in pairs)
    operations = [(vectors.fn.vector_add, operator.add),
                  (vectors.fn.vector_subtract, operator.sub),
                  (vectors.fn.vector_multiply, operator.mul)]
    if all(b != 0 for b in right):
        operations.append((vectors.fn.vector_divide, operator.truediv))
    for native, operation in operations:
        actual = native(left, right).one()
        for a, b, result in zip(left, right, actual, strict=True):
            exact = operation(Fraction(a), Fraction(b))
            if isinstance(a, float) or isinstance(b, float):
                assert isinstance(result.value, float)
                # Exact zero signs are covered independently by the Decimal matrix.
                assert result.value == 0.0 if exact == 0 else bits(result.value) == bits(nearest(exact))
            else:
                assert type(result.value) in (int, Fraction)
                assert result.value == exact


def test_vector_ieee_arithmetic(vectors):
    """Decimal supplies independent nonfinite and signed-zero scalar results."""
    numbers = [-math.inf, -3.0, -0.0, 0.0, 7.0, math.inf, math.nan,
               1 << 3000, -(1 << 3000)]
    pairs = [(a, b) for a, b in product(numbers, repeat=2)
             if any(isinstance(v, float) and (not math.isfinite(v) or v == 0.0) for v in (a, b))]
    left, right = tuple(a for a, _ in pairs), tuple(b for _, b in pairs)
    operations = [(vectors.fn.vector_add, operator.add),
                  (vectors.fn.vector_subtract, operator.sub),
                  (vectors.fn.vector_multiply, operator.mul),
                  (vectors.fn.vector_divide, operator.truediv)]
    with decimal.localcontext() as context:
        context.prec = 10000
        for signal in context.traps:
            context.traps[signal] = False
        for native, operation in operations:
            actual = native(left, right).one()
            for a, b, result in zip(left, right, actual, strict=True):
                expected = float(operation(decimal.Decimal(a), decimal.Decimal(b)))
                if math.isnan(expected):
                    assert math.isnan(result.value)
                else:
                    assert bits(result.value) == bits(expected)


def test_vector_nonfinite_dot_reduction(vectors):
    """A nonfinite accumulator does not turn huge finite operands into infinities."""
    numbers = [-math.inf, -0.0, 0.0, math.inf, math.nan, 1 << 3000, -(1 << 3000)]
    with decimal.localcontext() as context:
        context.prec = 10000
        for signal in context.traps:
            context.traps[signal] = False
        for left, right, accumulator in product(numbers, repeat=3):
            actual = vectors.fn.dot((left, accumulator), (right, 1)).one()
            expected = float(decimal.Decimal(0) + decimal.Decimal(left) * decimal.Decimal(right)
                             + decimal.Decimal(accumulator))
            if math.isnan(expected):
                assert math.isnan(actual)
            else:
                assert bits(actual) == bits(expected)


def test_vector_rationals_compose(vectors):
    """Returned rationals remain inputs to exact scalar and vector operations."""
    rational = vectors.fn.vector_divide((1, 2), (3, 3)).one()
    assert [value.value for value in rational] == [Fraction(1, 3), Fraction(2, 3)]
    assert vectors.fn.vector_scale(rational, 3).one() == (1, 2)
    assert vectors.fn.vector_add(rational, rational).one()[0].value == Fraction(2, 3)
    assert vectors.fn.vector_fill(2, rational[0]).one()[1].value == Fraction(1, 3)
    assert vectors.fn.cosine(rational, rational).one() == 1.0


def test_vector_seeded_construction(vectors):
    """The public held-body seed scope reaches Vector and restores its generator."""
    before = vectors.runtime.must("getrand(State)")["State"]
    body = S.random_normal_vector(4)
    first = vectors.fn.with_seed(17, body).one()
    assert first == vectors.fn.with_seed(17, body).one()
    assert first != vectors.fn.with_seed(18, body).one()
    assert len(first) == 4
    assert abs(vectors.fn.norm(first).one() - 1.0) < 1e-15
    assert vectors.runtime.must("getrand(State)")["State"] == before


@pytest.mark.parametrize("head,args,reason", [
    ("dot", ((1,), ()), "vector_dimensions"),
    ("norm", ((1, S.bad),), "number"),
    ("vector_divide", ((2, 1), (1, 0)), "zero_divisor"),
    ("vector_fill", (-1, 7), "nonneg"),
    ("random_normal_vector", (1.5,), "integer"),
])
def test_vector_refusals_name_the_operation(vectors, head, args, reason):
    """Invalid values produce a named operation exception instead of an empty answer."""
    with pytest.raises(MettaOperationError, match=reason) as refused:
        getattr(vectors.fn, head)(*args).one()
    assert head.replace("_", "-") in str(refused.value)


def test_vector_card_covers_its_native_surface():
    """The generated card carries every head, both random arities and its example."""
    card = library.card("lib_vector")
    assert len(card.heads) == len(card.documented) == 13
    assert sum(len(head.types) for head in card.heads) == 14
    assert "exact finite reductions" in card.doc
    assert card.doc in str(card)
    assert card.doc in card._repr_html_()
    assert card.doc in card.__rich__().caption.plain
    assert any(path.name == "13-vector_lib.metta" for path in card.examples)
