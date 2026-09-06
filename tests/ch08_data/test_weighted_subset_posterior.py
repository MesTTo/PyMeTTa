"""Purpose: verify lib_combinatorics' exact weighted-subset posterior surface.

The generated oracle enumerates only small cases. The shipped operation is the
independent sparse prefix/suffix implementation, so agreement proves its exact
mass and every marginal without copying or sharing implementation structure.

Guarantees:
  - exact mass and all marginals agree with exhaustive Fraction arithmetic,
    preserve identity and order, and are invariant under one shared loss scale
    [tested: test_weighted_subset_matches_exhaustive; commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]
  - conditioning on an exact unit-loss total makes the sum of posterior
    inclusion marginals equal that total [tested:
    test_unit_loss_marginals_sum_to_observation; commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]
  - malformed identity, lattice, prior, and zero-mass inputs refuse with their
    own remedies [tested: test_weighted_subset_refusals_name_the_remedy;
    commit=afc4024cef7d4b7bcdd194bb030a112187b676d0]
"""

from __future__ import annotations

from collections.abc import Iterator
from fractions import Fraction
from itertools import product
from math import gcd

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, Grounded, Space, Symbol
from metta.errors import EngineError


@pytest.fixture(scope="module")
def subset_space(metta) -> Iterator[Space]:
    """One isolated imported library shared by the generated examples.

    Dropped on the way out, because an import is not isolated by the space it
    is made in: a library's heads are compiled into the one module table this
    process has, so `lib_combinatorics`' `range` answered `is_function` in
    `&self` for every later test in the same worker. That is not academic --
    `list(range(n))` inside an `@m.define` then reads as ambiguous between an
    engine answer stream and a host list, which is what the compiler refuses,
    and test_list_collects_engine_answers_and_preserves_host_lists failed
    whenever this file ran before it [measured 2026-09-07: `pytest -n 0
    tests/ch08_data/test_weighted_subset_posterior.py <that test>` fails and
    the test alone passes]. Dropping the space withdraws the head, measured the
    same day: is_function('range') answers False again.
    """
    with metta._new_space() as space:
        space.run("!(import! (context-space) (library lib_combinatorics))")
        yield space


@st.composite
def _prior(draw) -> tuple[int, int]:
    denominator = draw(st.integers(min_value=1, max_value=9))
    numerator = draw(st.integers(min_value=0, max_value=denominator))
    return numerator, denominator


@st.composite
def _interior_prior(draw) -> tuple[int, int]:
    denominator = draw(st.integers(min_value=2, max_value=9))
    numerator = draw(st.integers(min_value=1, max_value=denominator - 1))
    return numerator, denominator


_ROWS = st.lists(
    st.tuples(st.integers(min_value=0, max_value=7), _prior()),
    min_size=0,
    max_size=7,
)


def _candidate_source(rows: list[tuple[str, int, int, int]]) -> str:
    return (
        "("
        + " ".join(
            f"(candidate {identity} {loss} (ratio {numerator} {denominator}))"
            for identity, loss, numerator, denominator in rows
        )
        + ")"
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


def _integer(atom) -> int:
    assert isinstance(atom, Grounded) and isinstance(atom.value, int), atom
    return atom.value


def _ratio(atom) -> Fraction:
    numerator, denominator = _tagged(atom, "ratio", 2)
    top, bottom = _integer(numerator), _integer(denominator)
    assert bottom > 0 and gcd(top, bottom) == 1
    return Fraction(top, bottom)


def _mass(space: Space, rows: list[tuple[str, int, int, int]], target: int) -> Fraction:
    answer = _one(
        space,
        f"(weighted-subset-mass-independent {_candidate_source(rows)} {target})",
    )
    return _ratio(answer)


def _posterior(
    space: Space, rows: list[tuple[str, int, int, int]], target: int
) -> tuple[Fraction, list[tuple[object, Fraction]]]:
    answer = _one(
        space,
        f"(weighted-subset-posterior-independent {_candidate_source(rows)} {target})",
    )
    mass_atom, marginals_atom = _tagged(answer, "subset-posterior", 2)
    assert isinstance(marginals_atom, Expression)
    marginals = []
    for row in marginals_atom:
        identity, probability = _tagged(row, "candidate-posterior", 2)
        if isinstance(identity, Symbol):
            key: object = identity.name
        else:
            assert isinstance(identity, Grounded)
            key = identity.value
        marginals.append((key, _ratio(probability)))
    return _ratio(mass_atom), marginals


def _exhaustive(
    rows: list[tuple[str, int, int, int]], target: int
) -> tuple[Fraction, list[Fraction] | None]:
    mass = Fraction(0)
    selected_mass = [Fraction(0) for _ in rows]
    for states in product((False, True), repeat=len(rows)):
        if (
            sum(loss for state, (_, loss, _, _) in zip(states, rows, strict=True) if state)
            != target
        ):
            continue
        probability = Fraction(1)
        for state, (_, _, numerator, denominator) in zip(states, rows, strict=True):
            prior = Fraction(numerator, denominator)
            probability *= prior if state else 1 - prior
        mass += probability
        for index, state in enumerate(states):
            if state:
                selected_mass[index] += probability
    if mass == 0:
        return mass, None
    return mass, [joint / mass for joint in selected_mass]


@given(raw_rows=_ROWS, target=st.integers(min_value=0, max_value=15), scale=st.integers(1, 5))
def test_weighted_subset_matches_exhaustive(subset_space, raw_rows, target, scale):
    """Every generated result agrees with a separately structured oracle."""
    rows = [
        (f"event-{index}", loss, numerator, denominator)
        for index, (loss, (numerator, denominator)) in enumerate(raw_rows)
    ]
    expected_mass, expected_marginals = _exhaustive(rows, target)
    assert _mass(subset_space, rows, target) == expected_mass

    if expected_marginals is None:
        with pytest.raises(EngineError, match="weighted-subset-mass-independent"):
            _posterior(subset_space, rows, target)
        return

    mass, marginals = _posterior(subset_space, rows, target)
    assert mass == expected_mass
    assert [identity for identity, _ in marginals] == [row[0] for row in rows]
    assert [probability for _, probability in marginals] == expected_marginals

    reversed_rows = list(reversed(rows))
    reversed_mass, reversed_marginals = _posterior(subset_space, reversed_rows, target)
    assert reversed_mass == mass
    assert dict(reversed_marginals) == dict(marginals)
    assert [identity for identity, _ in reversed_marginals] == [row[0] for row in reversed_rows]

    scaled_rows = [
        (identity, loss * scale, numerator, denominator)
        for identity, loss, numerator, denominator in rows
    ]
    assert _posterior(subset_space, scaled_rows, target * scale) == (mass, marginals)


@given(
    priors=st.lists(_interior_prior(), min_size=1, max_size=8),
    target=st.data(),
)
def test_unit_loss_marginals_sum_to_observation(subset_space, priors, target):
    """Conditioning on an exact count fixes the expected selected count."""
    observation = target.draw(st.integers(min_value=0, max_value=len(priors)))
    rows = [
        (f"unit-{index}", 1, numerator, denominator)
        for index, (numerator, denominator) in enumerate(priors)
    ]
    expected_mass, _ = _exhaustive(rows, observation)
    assert expected_mass > 0
    _, marginals = _posterior(subset_space, rows, observation)
    assert sum(probability for _, probability in marginals) == observation


def test_exact_identity_distinguishes_integer_and_float(subset_space):
    """PeTTa term identity keeps numeric lookalikes as separate events."""
    source = (
        "(weighted-subset-posterior-independent "
        "((candidate 1 0 (ratio 1 2)) (candidate 1.0 0 (ratio 1 2))) 0)"
    )
    answer = _one(subset_space, source)
    _, marginal_rows = _tagged(answer, "subset-posterior", 2)
    first, second = marginal_rows.children
    first_id, _ = _tagged(first, "candidate-posterior", 2)
    second_id, _ = _tagged(second, "candidate-posterior", 2)
    assert isinstance(first_id, Grounded) and first_id.value == 1
    assert isinstance(second_id, Grounded) and second_id.value == 1.0
    assert type(first_id.value) is int and type(second_id.value) is float


@pytest.mark.parametrize(
    ("source", "remedy"),
    [
        (
            "(weighted-subset-mass-independent ((candidate duplicate 1 (ratio 1 2)) (candidate duplicate 2 (ratio 1 2))) 1)",
            "distinct ground ID",
        ),
        (
            "(weighted-subset-mass-independent ((candidate $unbound 1 (ratio 1 2))) 1)",
            "ground acyclic ID",
        ),
        (
            "(weighted-subset-mass-independent ((candidate event 1.0 (ratio 1 2))) 1)",
            "shared integer scale",
        ),
        (
            "(weighted-subset-mass-independent ((candidate event -1 (ratio 1 2))) 1)",
            "nonnegative integer loss",
        ),
        (
            "(weighted-subset-mass-independent ((candidate event 1 (ratio 3 2))) 1)",
            "0 <= NUMERATOR <= DENOMINATOR",
        ),
        (
            "(weighted-subset-mass-independent ((candidate event 1 (ratio 1 2))) 1.0)",
            "nonnegative integer target",
        ),
        (
            "(weighted-subset-posterior-independent ((candidate event 1 (ratio 0 1))) 1)",
            "weighted-subset-mass-independent",
        ),
    ],
)
def test_weighted_subset_refusals_name_the_remedy(subset_space, source, remedy):
    """Each rejected contract points to this surface's supported correction."""
    with pytest.raises(EngineError, match=remedy):
        _one(subset_space, source)
