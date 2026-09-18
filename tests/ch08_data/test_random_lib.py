"""Purpose: model sample programs, literal occurrences and seeded replay.

Guarantees: generated populations preserve multiplicities; exact affine models
check rounding; program rewriting and recording use the ordinary Python doors.
[tested: test_random_lib.py; commit=1d0b78a359f58de49f2f98bed50a6480d56cd5f6].
"""

import math
from collections import Counter
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import G, S, V, lib
from metta._errors.errors import MettaError


@pytest.fixture(scope="module")
def randoms(metta):
    """Import the sample constructors and their MeTTa collection basis."""
    metta += lib.random
    return metta


SEEDS = st.integers(0, 1_000_000)
FINITE = st.floats(-1e200, 1e200, allow_nan=False, allow_infinity=False)


@given(st.lists(st.integers(-5, 5), max_size=14), st.integers(0, 30), SEEDS)
@settings(max_examples=80)
def test_occurrence_models(randoms, items, requested, seed):
    """A sample is a submultiset of the population and shuffle retains all entries."""
    count = requested % (len(items) + 1)
    sample = randoms.fn.with_seed(seed, S["random-sample!"](tuple(items), count))[0]
    actual = Counter(value.value for value in sample)
    assert len(sample) == count
    assert actual <= Counter(items)
    shuffled = randoms.fn.with_seed(seed, S["random-shuffle!"](tuple(items)))[0]
    assert Counter(value.value for value in shuffled) == Counter(items)


@given(FINITE, FINITE, SEEDS)
@settings(max_examples=80)
def test_uniform_uses_one_final_rounding(randoms, a, b, seed):
    """Fraction interpolation supplies a rounding oracle independent of Vector."""
    low, high = sorted((a, b))
    coordinate = randoms.fn.with_seed(seed, S.random_float(0, 1)).one()
    plan = randoms.fn.random_uniform(low, high)[0]
    actual = randoms.fn.with_seed(seed, plan).one()
    expected = low if low == high else float(
        (1 - Fraction(coordinate)) * Fraction(low) + Fraction(coordinate) * Fraction(high)
    )
    assert actual == expected
    assert low <= actual <= high


@given(st.floats(-1e100, 1e100, allow_nan=False, allow_infinity=False),
       st.floats(0, 1e100, allow_nan=False, allow_infinity=False), SEEDS)
@settings(max_examples=60)
def test_normal_uses_two_core_coordinates_and_exact_affine_rounding(randoms, mean, deviation, seed):
    """Box-Muller and a Fraction affine sum independently price the same coordinates."""
    coordinates = randoms.fn.with_seed(seed, S.repeat(2, S.random_float(0, 1)))
    u, v = (coordinate.value for coordinate in coordinates)
    z = math.cos(2 * math.pi * u) * math.sqrt(-2 * math.log(v))
    expected = mean if deviation == 0 else float(Fraction(mean) + Fraction(deviation) * Fraction(z))
    plan = randoms.fn.random_normal(mean, deviation)[0]
    assert randoms.fn.with_seed(seed, plan).one() == expected


def test_literal_programs_preserve_variable_sharing_and_host_objects(randoms):
    """Code remains data during construction, and sampled occurrences retain identity."""
    opaque = object()
    items = (V.x, V.x, V.y, S.Error(S.data, S.code), S["+"](1, 2), G(opaque))
    shuffled = randoms.fn["random-shuffle!"](items)[0]
    assert len(shuffled) == len(items)
    assert len(shuffled.vars) == 2
    assert sum(value == S.Error(S.data, S.code) for value in shuffled) == 1
    assert sum(value == S["+"](1, 2) for value in shuffled) == 1
    assert any(getattr(value, "value", None) is opaque for value in shuffled)
    chooser = randoms.fn.random_choice((V.x,))[0]
    repeated = randoms.fn.map_atom((0, 1, 2, 3), V.i, S.eval(chooser))[0]
    assert len(repeated.vars) == 1
    assert all(value == repeated[0] for value in repeated)


def test_sampler_programs_can_be_rewritten_and_constructors_reconstructed(randoms):
    """Replace entropy syntax and rebuild a constructor from its stored equation."""
    head, _entropy, low, high = randoms.fn.random_uniform(2, 10)[0]
    assert randoms.eval((head, 0.25, low, high)) == [4.0]
    row = randoms.match(S["="](S.random_normal(V.mean, V.deviation), V.body)).one()
    constructor = randoms.eval(S["|->"]((row.mean, row.deviation), row.body))[0]
    program = randoms.eval((constructor, 7, 0))[0]
    assert randoms.eval(program) == [7.0]
    choices = randoms.fn.random_normal(S.superpose((2, 3)), 0)
    assert [answer for choice in choices for answer in randoms.eval(choice)] == [2.0, 3.0]
    assert randoms.fn.repeat(2, S.superpose((S.a, S.b))) == [S.a, S.b, S.a, S.b]


@pytest.mark.parametrize("name,arguments", [
    ("random-uniform", (2, 1)), ("random-normal", (0, -1)),
    ("random-lognormal", (0, -1)), ("random-exponential", (0,)),
    ("random-triangular", (0, 1, 2)), ("random-gamma", (0, 1)),
    ("random-beta", (1, 0)), ("random-bernoulli", (1.1,)),
    ("random-pareto", (0,)), ("random-weibull", (1, 0)),
    ("random-normal", (math.inf, 1)), ("random-normal", (math.nan, 1)),
    ("random-choice", ((),)), ("random-shuffle!", (G("text"),)),
    ("random-sample!", ((1,), 2)), ("random-sample!", ((1,), -1)),
    ("random-sample!", ((1,), 1.0)),
])
def test_invalid_inputs_are_refused(randoms, name, arguments):
    """The public MeTTa error boundary covers numeric and structural refusals."""
    refusal = S.if_error(S.catch(S[name](*arguments)), S.refused, S.accepted)
    assert randoms.eval(refusal) == [S.refused]


@pytest.mark.parametrize("constructor,arguments", [
    ("random-uniform", (0, 1)), ("random-normal", (0, 1)),
    ("random-lognormal", (0, 1)), ("random-exponential", (1,)),
    ("random-triangular", (0, 1, 0.5)), ("random-gamma", (2, 1)),
    ("random-beta", (2, 3)), ("random-bernoulli", (0.4,)),
    ("random-pareto", (2,)), ("random-weibull", (2, 1)),
    ("random-choice", ((S.a, S.b, S.c),)),
])
def test_sample_program_recordings_replay_through_the_core_seed(randoms, constructor, arguments):
    """Seeded programs replay against the same visible specialization equations."""
    program = randoms.fn[constructor](*arguments)[0]
    recording = randoms.record(program, seed=42)
    assert recording.replayable is True
    assert recording.reason is None
    assert recording.seed == 42
    if recording.digest != randoms.digest():
        # Runtime specialization publishes equations. The recording retains its
        # starting atoms; that is intentionally a different content digest.
        with pytest.raises(MettaError, match="needs the space the recording was made over"):
            recording.replay(randoms)
        recording = randoms.record(program, seed=42)
        assert recording.replayable is True
        assert recording.digest == randoms.digest()
    assert list(recording.replay(randoms)) == list(recording.events)


@pytest.mark.parametrize("program", [
    S["random-sample!"]((S.a, S.b, S.c), 2),
    S["random-shuffle!"]((S.a, S.b, S.c)),
])
def test_occurrence_validation_keeps_recording_conservative(randoms, program):
    """A retained assertion may write diagnostics, which a seed cannot reproduce."""
    recording = randoms.record(program, seed=42)
    assert recording.replayable is False
    assert "assertEqualMsg" in recording.reason
    assert len(recording.events) > 0
    with pytest.raises(MettaError, match="not replayable"):
        recording.replay(randoms)
