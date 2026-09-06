"""Purpose: property-check lib_pln2's selected Beta and moment laws.

Guarantees:
  - confidence/count conversion, Beta moments, updates, independent products,
    and total probability agree with independently evaluated formulas over
    generated valid inputs [tested: test_confidence_count_round_trip,
    test_beta_moments_match_definition, test_supported_product_matches_the_formula,
    test_supported_total_probability_matches_the_formula; commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]
  - overlapping provenance and unidentifiable or invalid values refuse while
    naming the supported remedy [tested: test_support_overlap_refuses_factoring,
    test_pln2_numeric_refusals_name_the_remedy; commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]
  - every refusal renders its formal term as a sentence rather than as
    `Unknown error term` [tested:
    test_pln2_refusals_state_the_complaint_and_not_its_shape;
    commit=e34e8e386772b582ba24828138056c5d26be28f8]
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, Grounded, Space, Symbol
from metta.errors import EngineError


@pytest.fixture(scope="module")
def pln2_space(metta) -> Space:
    """One isolated imported truth library shared by generated examples."""
    space = metta._new_space()
    space.run("!(import! (context-space) (library lib_pln2))")
    return space


_PROBABILITY = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
    width=32,
)
_INTERIOR_PROBABILITY = st.floats(
    min_value=0.001,
    max_value=0.999,
    allow_nan=False,
    allow_infinity=False,
)
_POSITIVE = st.floats(
    min_value=0.01,
    max_value=1_000.0,
    allow_nan=False,
    allow_infinity=False,
)


def _one(space: Space, source: str):
    groups = space.run(f"!{source}")
    assert len(groups) == 1 and len(groups[0]) == 1, groups
    return groups[0][0]


def _tagged(atom, tag: str, arity: int) -> tuple:
    assert isinstance(atom, Expression), atom
    assert len(atom) == arity + 1, atom
    assert isinstance(atom[0], Symbol) and atom[0].name == tag, atom
    return atom.children[1:]


def _number(atom) -> float:
    assert isinstance(atom, Grounded), atom
    assert isinstance(atom.value, (int, float)) and not isinstance(atom.value, bool)
    return float(atom.value)


def _moments(atom) -> tuple[float, float]:
    mean, variance = _tagged(atom, "moments", 2)
    return _number(mean), _number(variance)


def _supported(atom) -> tuple[float, float, list[str]]:
    moments, support = _tagged(atom, "supported", 2)
    assert isinstance(support, Expression)
    identities = []
    for identity in support:
        assert isinstance(identity, Symbol)
        identities.append(identity.name)
    mean, variance = _moments(moments)
    return mean, variance, identities


def _valid_moments(mean: float, fraction: float) -> tuple[float, float]:
    return mean, mean * (1.0 - mean) * fraction


def test_petta_profile_matches_metta():
    """The requested profile spelling inherits the repository profile exactly."""
    from hypothesis import settings as hypothesis_settings

    assert hypothesis_settings.get_profile("petta") == hypothesis_settings.get_profile("metta")


@given(confidence=st.floats(min_value=0.0, max_value=0.999, allow_nan=False), scale=_POSITIVE)
def test_confidence_count_round_trip(pln2_space, confidence, scale):
    """Explicit evidence scale makes both directions reciprocal."""
    count = _number(_one(pln2_space, f"(pln2-confidence-count {confidence!r} {scale!r})"))
    restored = _number(_one(pln2_space, f"(pln2-count-confidence {count!r} {scale!r})"))
    assert restored == pytest.approx(confidence, rel=2e-12, abs=2e-12)


@given(alpha=_POSITIVE, beta=_POSITIVE)
def test_beta_moments_match_definition(pln2_space, alpha, beta):
    """Generated shapes agree with the standard Beta moments."""
    mean, variance = _moments(_one(pln2_space, f"(pln2-beta-moments (beta {alpha!r} {beta!r}))"))
    total = alpha + beta
    assert mean == pytest.approx(alpha / total)
    assert variance == pytest.approx(alpha * beta / (total * total * (total + 1)))
    assert 0 < mean < 1
    assert 0 < variance <= mean * (1 - mean)


@given(alpha=_POSITIVE, beta=_POSITIVE, successes=st.integers(0, 100), failures=st.integers(0, 100))
def test_beta_update_adds_observations(pln2_space, alpha, beta, successes, failures):
    """The posterior shapes add exactly the two observed sufficient statistics."""
    answer = _one(
        pln2_space,
        f"(pln2-beta-update (beta {alpha!r} {beta!r}) {successes} {failures})",
    )
    updated_alpha, updated_beta = _tagged(answer, "beta", 2)
    assert _number(updated_alpha) == pytest.approx(alpha + successes)
    assert _number(updated_beta) == pytest.approx(beta + failures)


@given(
    left_mean=_PROBABILITY,
    left_fraction=_PROBABILITY,
    right_mean=_PROBABILITY,
    right_fraction=_PROBABILITY,
)
def test_supported_product_matches_the_formula(
    pln2_space, left_mean, left_fraction, right_mean, right_fraction
):
    """Independent product propagation agrees with its exact second moment."""
    left_mean, left_variance = _valid_moments(left_mean, left_fraction)
    right_mean, right_variance = _valid_moments(right_mean, right_fraction)
    answer = _one(
        pln2_space,
        "(pln2-product-independent "
        f"(supported (moments {left_mean!r} {left_variance!r}) (left-source)) "
        f"(supported (moments {right_mean!r} {right_variance!r}) (right-source)))",
    )
    mean, variance, support = _supported(answer)
    expected_mean = left_mean * right_mean
    expected_variance = (
        left_variance * right_variance
        + left_variance * right_mean * right_mean
        + right_variance * left_mean * left_mean
    )
    assert mean == pytest.approx(expected_mean, abs=1e-14)
    assert variance == pytest.approx(expected_variance, abs=1e-14)
    assert support == ["left-source", "right-source"]


@given(
    true_mean=_PROBABILITY,
    true_fraction=_PROBABILITY,
    false_mean=_PROBABILITY,
    false_fraction=_PROBABILITY,
    condition_mean=_PROBABILITY,
    condition_fraction=_PROBABILITY,
)
def test_supported_total_probability_matches_the_formula(  # noqa: PLR0917  -- each parameter is one drawn strategy, and hypothesis injects them by name
    pln2_space,
    true_mean,
    true_fraction,
    false_mean,
    false_fraction,
    condition_mean,
    condition_fraction,
):
    """Conditional total probability propagates all independent variance terms."""
    true_mean, true_variance = _valid_moments(true_mean, true_fraction)
    false_mean, false_variance = _valid_moments(false_mean, false_fraction)
    condition_mean, condition_variance = _valid_moments(condition_mean, condition_fraction)
    answer = _one(
        pln2_space,
        "(pln2-total-probability-independent "
        f"(supported (moments {true_mean!r} {true_variance!r}) (if-true)) "
        f"(supported (moments {false_mean!r} {false_variance!r}) (if-false)) "
        f"(supported (moments {condition_mean!r} {condition_variance!r}) (condition)))",
    )
    mean, variance, support = _supported(answer)
    complement = 1 - condition_mean
    difference = true_mean - false_mean
    expected_mean = true_mean * condition_mean + false_mean * complement
    expected_variance = (
        condition_mean**2 * true_variance
        + complement**2 * false_variance
        + difference**2 * condition_variance
        + condition_variance * (true_variance + false_variance)
    )
    assert mean == pytest.approx(expected_mean, abs=1e-14)
    assert variance == pytest.approx(expected_variance, abs=1e-14)
    assert support == ["if-true", "if-false", "condition"]


@given(
    mean=_INTERIOR_PROBABILITY,
    confidence=st.floats(min_value=0.0, max_value=0.999, allow_nan=False),
    scale=_POSITIVE,
)
def test_stv_moment_round_trip(pln2_space, mean, confidence, scale):
    """Finite interior STVs round-trip through moments under one explicit scale."""
    moments = _one(
        pln2_space,
        f"(pln2-stv-moments (stv {mean!r} {confidence!r}) {scale!r})",
    )
    moment_mean, variance = _moments(moments)
    answer = _one(
        pln2_space,
        f"(pln2-moments-stv (moments {moment_mean!r} {variance!r}) {scale!r})",
    )
    restored_mean, restored_confidence = _tagged(answer, "stv", 2)
    assert _number(restored_mean) == pytest.approx(mean)
    assert _number(restored_confidence) == pytest.approx(confidence, abs=2e-12)


def test_support_overlap_refuses_factoring(pln2_space):
    """Shared evidence cannot be silently counted as independent evidence."""
    source = (
        "(pln2-product-independent "
        "(supported (moments 0.5 0.1) (shared left)) "
        "(supported (moments 0.4 0.1) (shared right)))"
    )
    with pytest.raises(EngineError, match=r"factor shared support.*owned reasoner"):
        _one(pln2_space, source)


@pytest.mark.parametrize(
    ("source", "remedy"),
    [
        ("(pln2-confidence-count 1.0 800.0)", "infinite evidence count"),
        ("(pln2-confidence-count 0.5 0.0)", "greater than zero"),
        ("(pln2-beta-moments (beta 0.0 1.0))", "positive shape parameters"),
        (
            "(pln2-moments-stv (moments 0.0 0.0) 1.0)",
            "does not identify finite Beta concentration",
        ),
        (
            "(pln2-moments-stv (moments 0.5 0.0) 1.0)",
            "zero variance denotes unbounded concentration",
        ),
        (
            "(pln2-product-independent (supported (moments 0.5 0.3) (a)) (supported (moments 0.5 0.1) (b)))",
            "VARIANCE <= MEAN",
        ),
        (
            "(pln2-require-independent-supports ((same same)))",
            "list each evidence ID once",
        ),
    ],
)
def test_pln2_numeric_refusals_name_the_remedy(pln2_space, source, remedy):
    """A rejected value says how to represent the supported case."""
    with pytest.raises(EngineError, match=remedy):
        _one(pln2_space, source)


@pytest.mark.parametrize(
    ("source", "complaint"),
    [
        ("(pln2-moments-stv (moments 170.0 25.0) 100.0)", "the mean is 170"),
        ("(pln2-stv-moments (moments 0.5 0.1) 100.0)", "is not a truth value"),
        ("(pln2-beta-moments (stv 1.0 0.5))", "is not a Beta distribution"),
        ("(pln2-confidence-count 1.0 800.0)", "the confidence is 1.0"),
        (
            "(pln2-moments-stv (moments 0.5 0.0) 1.0)",
            "leaves the Beta concentration unbounded",
        ),
        (
            "(pln2-product-independent (supported (moments 0.5 0.01) (a))"
            " (supported (moments 0.5 0.01) (a)))",
            "supports more than one operand",
        ),
    ],
)
def test_pln2_refusals_state_the_complaint_and_not_its_shape(pln2_space, source, complaint):
    """The thrown term renders as a sentence, beside the remedy it travels with.

    A refusal carries two halves: the formal term says what was WRONG and the
    context says what to DO. Only the second had a renderer, so a caller who
    passed a height distribution where a truth value belongs read
    `Unknown error term: pln2_invalid_probability(mean,170)`, which is the
    shape of the complaint rather than the complaint. The clauses are
    `prolog:error_message//1` and not `message//1`, because SWI dispatches the
    formal half of an `error(Formal, Context)` pair through that hook alone,
    so this also pins the hook the library chose.
    """
    with pytest.raises(EngineError) as refused:
        _one(pln2_space, source)
    message = str(refused.value)
    assert complaint in message, message
    assert "Unknown error term" not in message, message
