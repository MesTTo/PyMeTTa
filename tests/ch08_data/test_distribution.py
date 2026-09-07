"""Purpose: prove the laws of lib_distribution over generated finite supports.

Assumes:
  - generated rows use positive integer weights and integer outcomes; binary64
    comparisons use numerical tolerance while separate dyadic fixtures demand
    exact weights.
Guarantees:
  - normalization, unary map, independent product, threshold, strict win
    probability, exact joint conditioning, independent average, and Bernoulli
    addition satisfy their stated laws over 100 generated examples per property
    [tested: this module with HYPOTHESIS_PROFILE=ci; commit=f99382c5b4127b49de6e0a6e355d50eda39c5df6].
  - empty, zero, negative, and nonfinite mass expose exact remedy-bearing Error
    messages through normalization and every composition operation [tested:
    test_invalid_distributions_refuse_with_a_remedy,
    test_operations_preserve_the_normalization_refusal,
    test_average_preserves_a_refusal_at_every_input_position; commit=f99382c5b4127b49de6e0a6e355d50eda39c5df6].
Owns resources:
  - distribution_space closes its module-scoped fresh Space when the fixture
    exits.
"""

from __future__ import annotations

import math
from collections import OrderedDict

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, Grounded, S

ROWS = st.lists(
    st.tuples(
        st.integers(min_value=1, max_value=8),
        st.integers(min_value=-8, max_value=8),
    ),
    min_size=1,
    max_size=4,
)
BERNOULLI_P = st.sampled_from([0.0, 0.25, 0.5, 0.75, 1.0])
LAW_SETTINGS = settings(max_examples=100)


@st.composite
def joint_cases(draw):
    """A nonempty finite joint support and an observation it contains."""
    generated = draw(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=8),
                st.integers(min_value=-4, max_value=4),
                st.integers(min_value=-8, max_value=8),
            ),
            min_size=1,
            max_size=4,
        )
    )
    observed = draw(st.sampled_from([left for _weight, left, _right in generated]))
    return generated, observed


@pytest.fixture(scope="module")
def distribution_space(metta):
    """Provide a fresh space containing the library and test-only functions."""
    with metta._new_space() as space:
        space.run("!(import! (context-space) (library lib_distribution))")
        space.run(
            """
            (= (distribution-test-inc $x) (+ $x 1))
            (= (distribution-test-add $x $y) (+ $x $y))
            (= (distribution-test-pair-sum $pair)
               (+ (index-atom $pair 1) (index-atom $pair 2)))
            """
        )
        yield space


def distribution(generated):
    """Build transparent weight-first rows without parsing generated data."""
    return Expression(
        *(Expression(Grounded(weight), Grounded(value)) for weight, value in generated)
    )


def joint_distribution(generated):
    """Build weight-first rows whose values are explicit ``Pair`` atoms."""
    return Expression(
        *(
            Expression(
                Grounded(weight),
                Expression(S.Pair, Grounded(left), Grounded(right)),
            )
            for weight, left, right in generated
        )
    )


def call(space, name, *arguments):
    """Evaluate one public library call and require its deterministic answer."""
    answers = space.eval(Expression(S[name], *arguments))
    assert len(answers) == 1, f"{name} answered {answers!r}"
    return answers[0]


def number(atom):
    """Read a numeric grounded answer."""
    assert isinstance(atom, Grounded), atom
    return atom.value


def error_message(atom):
    """Read the reason from one MeTTa ``(Error culprit reason)`` answer."""
    assert atom.children[0] == S.Error
    return atom.children[2].value


def rows(atom):
    """Read numeric outcome rows as ordered ``(outcome, mass)`` pairs."""
    return [(number(pair.children[1]), number(pair.children[0])) for pair in atom.children]


def masses(atom):
    """Read a numeric distribution by outcome, ignoring representation order."""
    return dict(rows(atom))


def normalized(generated):
    """The Python oracle for stable duplicate collapse and normalization."""
    collapsed = OrderedDict()
    for weight, outcome in generated:
        collapsed[outcome] = collapsed.get(outcome, 0) + weight
    total = sum(collapsed.values())
    return OrderedDict((outcome, weight / total) for outcome, weight in collapsed.items())


def assert_masses_close(actual, expected):
    """Compare two finite PMFs after their outcomes have been aligned."""
    actual_masses = masses(actual)
    assert actual_masses.keys() == expected.keys()
    for outcome, expected_mass in expected.items():
        assert actual_masses[outcome] == pytest.approx(expected_mass, abs=1e-12)


@LAW_SETTINGS
@given(generated=ROWS)
def test_normalization_is_idempotent_ordered_and_unit_mass(distribution_space, generated):
    """Normalization is a stable, idempotent probability projection."""
    first = call(distribution_space, "ws-normalize", distribution(generated))
    second = call(distribution_space, "ws-normalize", first)
    expected = normalized(generated)

    assert [outcome for outcome, _mass in rows(first)] == list(expected)
    assert_masses_close(first, expected)
    assert_masses_close(second, expected)
    assert math.fsum(mass for _outcome, mass in rows(first)) == pytest.approx(1.0)


@LAW_SETTINGS
@given(generated=ROWS)
def test_map2_with_a_point_mass_is_unary_map(distribution_space, generated):
    """Adding a point mass through map2 agrees with unary increment."""
    dist = distribution(generated)
    point = distribution([(1, 1)])
    binary = call(
        distribution_space,
        "ws-map2-independent",
        S["distribution-test-add"],
        dist,
        point,
    )
    unary = call(
        distribution_space,
        "ws-map",
        S["distribution-test-inc"],
        dist,
    )
    assert_masses_close(binary, masses(unary))


@LAW_SETTINGS
@given(left=ROWS, right=ROWS, third=ROWS)
def test_additive_convolution_is_commutative_associative_and_linear(
    distribution_space, left, right, third
):
    """Independent addition obeys its algebraic and expectation laws."""
    add = S["distribution-test-add"]
    a, b, c = distribution(left), distribution(right), distribution(third)
    ab = call(distribution_space, "ws-map2-independent", add, a, b)
    ba = call(distribution_space, "ws-map2-independent", add, b, a)
    assert_masses_close(ab, masses(ba))

    left_grouped = call(distribution_space, "ws-map2-independent", add, ab, c)
    bc = call(distribution_space, "ws-map2-independent", add, b, c)
    right_grouped = call(distribution_space, "ws-map2-independent", add, a, bc)
    assert_masses_close(left_grouped, masses(right_grouped))

    normal_a = call(distribution_space, "ws-normalize", a)
    normal_b = call(distribution_space, "ws-normalize", b)
    ea = number(call(distribution_space, "ws-expect", normal_a))
    eb = number(call(distribution_space, "ws-expect", normal_b))
    eab = number(call(distribution_space, "ws-expect", ab))
    assert eab == pytest.approx(ea + eb, abs=1e-10)


@LAW_SETTINGS
@given(generated=ROWS)
def test_threshold_boundaries_cover_the_support(distribution_space, generated):
    """Inclusive threshold mass spans one at the minimum and zero above it."""
    dist = distribution(generated)
    outcomes = [outcome for _weight, outcome in generated]
    at_minimum = number(call(distribution_space, "ws-mass-at-least", dist, Grounded(min(outcomes))))
    above_maximum = number(
        call(distribution_space, "ws-mass-at-least", dist, Grounded(max(outcomes) + 1))
    )
    assert at_minimum == pytest.approx(1.0)
    assert above_maximum == 0.0


@LAW_SETTINGS
@given(left=ROWS, right=ROWS)
def test_strict_independent_win_probability_matches_the_cartesian_oracle(
    distribution_space, left, right
):
    """Strict comparison sums exactly the winning Cartesian pairs."""
    actual = number(
        call(
            distribution_space,
            "ws-prob-gt-independent",
            distribution(left),
            distribution(right),
        )
    )
    a, b = normalized(left), normalized(right)
    expected = sum(
        left_mass * right_mass
        for left_value, left_mass in a.items()
        for right_value, right_mass in b.items()
        if left_value > right_value
    )
    assert actual == pytest.approx(expected, abs=1e-12)


@LAW_SETTINGS
@given(case=joint_cases())
def test_exact_joint_conditioning_matches_the_selected_slice(distribution_space, case):
    """Conditioning selects and normalizes the observed joint slice."""
    generated, observed = case
    actual = call(
        distribution_space,
        "ws-condition-joint",
        joint_distribution(generated),
        Grounded(observed),
    )
    expected = normalized(
        [(weight, right) for weight, left, right in generated if left == observed]
    )
    assert_masses_close(actual, expected)


@LAW_SETTINGS
@given(generated=st.lists(ROWS, min_size=1, max_size=3))
def test_independent_average_has_unit_mass_and_mean_expectation(distribution_space, generated):
    """An independent average is normalized and has the mean expectation."""
    input_dists = [distribution(items) for items in generated]
    actual = call(
        distribution_space,
        "ws-average-independent",
        Expression(*input_dists),
    )
    expected_mean = sum(
        sum(value * mass for value, mass in normalized(items).items()) for items in generated
    ) / len(generated)
    actual_mean = number(call(distribution_space, "ws-expect", actual))
    assert math.fsum(mass for _outcome, mass in rows(actual)) == pytest.approx(1.0)
    assert actual_mean == pytest.approx(expected_mean, abs=1e-10)


@LAW_SETTINGS
@given(generated=ROWS, probability=BERNOULLI_P)
def test_bernoulli_addition_is_independent_convolution(distribution_space, generated, probability):
    """Bernoulli addition is the public independent product construction."""
    dist = distribution(generated)
    actual = call(
        distribution_space,
        "ws-add-bernoulli-independent",
        dist,
        Grounded(probability),
    )
    expected = call(
        distribution_space,
        "ws-map2-independent",
        S["distribution-test-add"],
        dist,
        distribution([(1.0 - probability, 0), (probability, 1)]),
    )
    assert_masses_close(actual, masses(expected))


def test_pair_order_duplicate_collapse_and_exact_dyadic_weights(distribution_space):
    """Left-major traversal and first-position collapse preserve dyadics."""
    actual = call(
        distribution_space,
        "ws-map2-independent",
        S["distribution-test-add"],
        distribution([(0.25, 0), (0.75, 1)]),
        distribution([(0.5, 0), (0.5, 1)]),
    )
    assert rows(actual) == [(0, 0.125), (1, 0.5), (2, 0.375)]

    distinct_numbers = call(
        distribution_space,
        "ws-normalize",
        Expression(
            Expression(Grounded(0.25), Grounded(1)),
            Expression(Grounded(0.75), Grounded(1.0)),
        ),
    )
    outcomes = [pair.children[1].value for pair in distinct_numbers.children]
    assert [type(outcome) for outcome in outcomes] == [int, float]
    assert rows(distinct_numbers) == [(1, 0.25), (1.0, 0.75)]

    overflow_safe = call(
        distribution_space,
        "ws-normalize",
        distribution([(1.0e308, 0), (1.0e308, 1)]),
    )
    assert rows(overflow_safe) == [(0, 0.5), (1, 0.5)]

    overflow_duplicate = call(
        distribution_space,
        "ws-normalize",
        distribution([(1.0e308, 0), (1.0e308, 0)]),
    )
    assert rows(overflow_duplicate) == [(0, 1.0)]


def test_independent_marginals_and_a_correlated_joint_are_not_interchangeable(
    distribution_space,
):
    """A joint law preserves correlation that two marginals cannot carry."""
    marginal = distribution([(0.5, 0), (0.5, 1)])
    independent = call(
        distribution_space,
        "ws-map2-independent",
        S["distribution-test-add"],
        marginal,
        marginal,
    )
    correlated = joint_distribution([(0.5, 0, 0), (0.5, 1, 1)])
    correlated_sum = call(
        distribution_space,
        "ws-map",
        S["distribution-test-pair-sum"],
        correlated,
    )
    conditioned = call(
        distribution_space,
        "ws-condition-joint",
        correlated,
        Grounded(1),
    )

    assert rows(independent) == [(0, 0.25), (1, 0.5), (2, 0.25)]
    assert rows(correlated_sum) == [(0, 0.5), (2, 0.5)]
    assert rows(conditioned) == [(1, 1.0)]


@pytest.mark.parametrize(
    ("dist", "message"),
    [
        (
            Expression(),
            "ws-normalize requires a nonempty finite distribution; provide at least one positive-weight outcome",
        ),
        (
            distribution([(0.0, 0)]),
            "ws-normalize requires positive total mass; provide at least one positive-weight outcome",
        ),
        (
            distribution([(-1.0, 0)]),
            "ws-normalize requires nonnegative weights; remove negative weights and provide at least one positive-weight outcome",
        ),
        (
            distribution([(2.0, 0), (-1.0, 1)]),
            "ws-normalize requires nonnegative weights; remove negative weights and provide at least one positive-weight outcome",
        ),
        (
            distribution([(math.inf, 0)]),
            "ws-normalize requires finite weights; replace NaN or infinite weights with finite nonnegative weights",
        ),
        (
            distribution([(math.nan, 0)]),
            "ws-normalize requires finite weights; replace NaN or infinite weights with finite nonnegative weights",
        ),
    ],
)
def test_invalid_distributions_refuse_with_a_remedy(distribution_space, dist, message):
    """Every invalid mass class returns its exact reader-facing remedy."""
    error = call(distribution_space, "ws-normalize", dist)
    assert error_message(error) == message


def test_operations_preserve_the_normalization_refusal(distribution_space):
    """Composition returns an invalid input's remedy without secondary errors."""
    empty = Expression()
    negative = distribution([(-1, 0)])
    zero = distribution([(0, 0)])
    valid = distribution([(1, 0)])
    expected_empty = (
        "ws-normalize requires a nonempty finite distribution; provide at least "
        "one positive-weight outcome"
    )
    expected_negative = (
        "ws-normalize requires nonnegative weights; remove negative weights and "
        "provide at least one positive-weight outcome"
    )
    expected_zero = (
        "ws-normalize requires positive total mass; provide at least one positive-weight outcome"
    )
    calls = [
        ("ws-map", (S["distribution-test-inc"], empty), expected_empty),
        ("ws-map", (S["distribution-test-inc"], negative), expected_negative),
        ("ws-map", (S["distribution-test-inc"], zero), expected_zero),
        (
            "ws-map2-independent",
            (S["distribution-test-add"], valid, empty),
            expected_empty,
        ),
        (
            "ws-map2-independent",
            (S["distribution-test-add"], negative, valid),
            expected_negative,
        ),
        ("ws-mass-at-least", (empty, Grounded(0)), expected_empty),
        (
            "ws-prob-gt-independent",
            (empty, valid),
            expected_empty,
        ),
        ("ws-condition-joint", (empty, Grounded(0)), expected_empty),
        ("ws-average-independent", (Expression(empty),), expected_empty),
        (
            "ws-add-bernoulli-independent",
            (empty, Grounded(0.5)),
            expected_empty,
        ),
    ]

    for name, arguments, message in calls:
        assert error_message(call(distribution_space, name, *arguments)) == message


def test_average_preserves_a_refusal_at_every_input_position(distribution_space):
    """The average fold short-circuits the first invalid distribution."""
    valid = distribution([(1, 0)])
    invalids = [
        (
            Expression(),
            "ws-normalize requires a nonempty finite distribution; provide at least one positive-weight outcome",
        ),
        (
            distribution([(0, 0)]),
            "ws-normalize requires positive total mass; provide at least one positive-weight outcome",
        ),
        (
            distribution([(-1, 0)]),
            "ws-normalize requires nonnegative weights; remove negative weights and provide at least one positive-weight outcome",
        ),
    ]

    for invalid, message in invalids:
        for position in range(3):
            inputs = [valid, valid]
            inputs.insert(position, invalid)
            error = call(
                distribution_space,
                "ws-average-independent",
                Expression(*inputs),
            )
            assert error.children[1] == invalid
            assert error_message(error) == message


def test_operation_specific_empty_cases_refuse_with_a_remedy(distribution_space):
    """Operations with extra domains explain how to repair invalid calls."""
    average_error = call(distribution_space, "ws-average-independent", Expression())
    assert error_message(average_error) == (
        "ws-average-independent requires at least one distribution; provide a "
        "nonempty expression of independent distributions"
    )

    condition_error = call(
        distribution_space,
        "ws-condition-joint",
        joint_distribution([(1, 0, 1)]),
        Grounded(2),
    )
    assert error_message(condition_error) == (
        "ws-condition-joint requires positive mass for the observed value; "
        "choose an observation in the joint support"
    )

    for invalid_probability in (-0.1, 1.1, math.inf, math.nan):
        probability_error = call(
            distribution_space,
            "ws-add-bernoulli-independent",
            distribution([(1, 0)]),
            Grounded(invalid_probability),
        )
        assert error_message(probability_error) == (
            "ws-add-bernoulli-independent requires p in [0, 1]; provide a valid "
            "Bernoulli probability"
        )
