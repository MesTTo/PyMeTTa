"""Purpose: pin algebra carriers on match, call, scope, sampling, and answers.

Guarantees:
  - counting uses the engine aggregate for both query and call bags, including
    duplicate derivations [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    test_counting_counts_duplicate_call_answers_inside_the_engine,
    test_counting_inference_growth_is_linear_when_answers_grow_in_depth;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - ordered carriers determine answer order before an Answers slice selects
    its prefix [tested:
    test_ranked_and_tropical_slices_are_stable_best_prefixes;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - a retained derivation can be explained and reinterpreted without asking
    its provider again [tested:
    test_provenance_retains_a_derivation_for_no_requery_reinterpretation,
    test_tagged_call_answers_use_the_carrier_without_hijacking_other_calls;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - the algebra satellite is its callable constructor while keeping module
    identity, and Space.sample uses random.choices vocabulary [tested:
    test_algebra_module_is_the_constructor_and_the_old_space_doors_are_retired,
    test_space_sample_is_seeded_and_uses_k_vocabulary; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - carrier selection stays lazy and its ContextVar crosses the async worker
    [tested: test_under_answers_defers_its_tagged_route_probe_until_pull,
    test_scoped_under_crosses_the_async_worker_context,
    test_under_refuses_none_and_restores_after_an_exception; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

import metta as metta_module
from metta import Answer, S, V, aio, counting, prov, ranked, tropical
from metta.foreign import SpaceProvider
from metta.vocabularies import Semiring


class _ScoredRows(SpaceProvider):
    """A provider whose annotations make ordering and provenance observable."""

    def __init__(self, rows):
        self.rows = rows
        self.asks = 0

    def atoms(self):
        return iter(())

    def match(self, pattern, *, limit=None):  # noqa: ARG002 -- the provider protocol requires the pattern argument
        self.asks += 1
        for value, annotation in self.rows[:limit]:
            yield Answer(value=S.score(value), k=annotation)


def test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor(
    metta, monkeypatch
):
    """The idiomatic count does not construct or pull the row cursor."""
    with metta._new_space() as facts:
        facts.add(S.edge(S.a, S.b), S.edge(S.a, S.b), S.edge(S.a, S.c))

        def cursor_must_not_open(*_args, **_kwargs):
            msg = "under=counting opened the materialising cursor"
            raise AssertionError(msg)

        monkeypatch.setattr("metta._space.Cursor", cursor_must_not_open)
        counted = facts.match(S.edge(S.a, V.x), under=counting)
        with facts.stats() as measured:
            assert counted.one() == 3

        assert measured.inferences > 0
        assert len(counted._cache) == 1
        assert facts.match(S.absent(V.x), under=counting).one() == 0


def test_counting_counts_duplicate_call_answers_inside_the_engine(metta):
    """Equal answers from distinct equations remain two bag derivations."""
    with metta._new_space() as program:
        program.run(
            "(= (under-call) same)\n"
            "(= (under-call) same)\n"
            "(= (under-call) other)"
        )
        with program.stats() as measured:
            assert program.answers(S.under_call(), under=counting).one() == 3
        assert measured.inferences > 0


def test_counting_inference_growth_is_linear_when_answers_grow_in_depth(metta):
    """Stats expose the no-row path: doubling deep answers stays subquadratic."""

    def measured(size):
        with metta._new_space() as facts:
            value = S.Z
            atoms = []
            for _ in range(size):
                atoms.append(S.num(value))
                value = S.S(value)
            facts.add(*atoms)
            with facts.stats() as stats:
                assert facts.match(S.num(V.value), under=counting).one() == size
            return stats.inferences

    shallow = measured(128)
    deep = measured(256)
    assert deep < 3 * shallow


def test_scoped_under_is_task_local_and_explicit_under_wins(metta):
    """Nested scopes restore, while a per-ask carrier outranks the scope."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.b))
        facts.run("(= (scoped-call) same)\n(= (scoped-call) same)")
        with metta_module_under(counting):
            assert facts.match(S.item(V.x)).one() == 2
            assert facts.fn.scoped_call().one() == 2
            with metta_module_under(tropical):
                assert facts.match(S.item(V.x), under=counting).one() == 2
            assert facts.match(S.item(V.x)).one() == 2
        assert [str(row.x) for row in facts.match(S.item(V.x))] == ["a", "b"]


def test_scoped_under_crosses_the_async_worker_context(metta):
    """The copied ContextVar reaches AsyncMeTTa's owning engine worker."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.b))

        async def ask():
            async with aio.AsyncMeTTa(metta=facts) as worker:
                with metta_module_under(counting):
                    counted = await worker.match(S.item(V.x))
                return counted.one()

        assert asyncio.run(ask()) == 2


def test_under_refuses_none_and_restores_after_an_exception(metta):
    """None is not a carrier, and exceptional scope exit restores the bag."""

    class ScopeError(Exception):
        pass

    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.b))
        with pytest.raises(TypeError, match="algebra carrier"):
            facts.match(S.item(V.x), under=None)
        with pytest.raises(ScopeError):
            with metta_module_under(counting):
                raise ScopeError
        assert [str(row.x) for row in facts.match(S.item(V.x))] == ["a", "b"]


def metta_module_under(carrier):
    """Keep the exact public spelling visible in the test body."""
    return metta_module.under(carrier)


def test_ranked_and_tropical_slices_are_stable_best_prefixes(metta):
    """Descending rank and ascending cost both preserve emission-order ties."""
    rows = [(S.low, 1), (S.best_a, 9), (S.best_b, 9), (S.middle, 4)]
    provider = _ScoredRows(rows)
    metta._register_space(provider, "&under-ranked")
    scores = metta._at("&under-ranked")

    assert [str(value) for value in scores.match(S.score(V.x), under=ranked)[:2].x] == [
        "best-a",
        "best-b",
    ]
    assert [str(value) for value in scores.match(S.score(V.x), under=tropical)[:2].x] == [
        "low",
        "middle",
    ]

    duplicates = _ScoredRows([(S.same, 5), (S.same, 5)])
    metta._register_space(duplicates, "&under-ranked-duplicates")
    repeated = metta._at("&under-ranked-duplicates")
    assert len(list(repeated.match(S.score(V.x), under=ranked))) == 2

    def scored_call(_query):
        for value, annotation in rows:
            yield Answer(value=value, k=annotation)

    metta.op(scored_call, name="under-scored-call")
    with metta._new_space() as program:
        best = program.answers(S.under_scored_call(S.query), under=ranked)[:2]
        assert [answer.value for answer in best] == [S.best_a, S.best_b]


def test_provenance_retains_a_derivation_for_no_requery_reinterpretation(metta):
    """why/under consume the captured carrier tree rather than the provider."""
    provider = _ScoredRows([("rain", S.src(S.weather_db))])
    metta._register_space(provider, "&under-prov")
    answer = metta._at("&under-prov").match(S.score(V.x), under=prov).first()

    assert "weather-db" in answer.why().render()
    assert answer.under(counting).annotation == 1
    assert provider.asks == 1


def test_tagged_derivations_flow_through_match_and_reinterpret_without_requery(
    metta,
):
    """The former evaluate_algebra capability lives behind match(under=)."""
    metta.algebra(
        "under-product",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    with metta._new_space() as program:
        program.add_tagged_fact(2, S.parent(S.tom, S.bob))
        program.add_tagged_fact(3, S.parent(S.bob, S.ann))
        program.add_tagged_rule(
            1,
            S.grandparent(V.x, V.z),
            S.parent(V.x, V.y),
            S.parent(V.y, V.z),
        )
        answer = program.match(
            S.grandparent(S.tom, S.ann), under=S.under_product
        ).one()
        assert answer.annotation == 6
        assert answer.under(counting).annotation == 1
        assert "grandparent" in answer.why().render()
        assert program.match(
            S.grandparent(S.tom, S.ann), under=counting
        ).one() == 1


def test_tagged_call_answers_use_the_carrier_without_hijacking_other_calls(metta):
    """Tagged routing is query-specific and both call kinds keep their values."""
    metta.algebra(
        "under-call-product",
        combine="+",
        extend="*",
        zero=0,
        one=1,
    )
    with metta._new_space() as program:
        program.add_tagged_fact(7, S.tagged_call(S.yes))
        program.run("(= (ordinary-call) ordinary)")

        tagged = program.answers(
            S.tagged_call(V.value), under="under-call-product"
        )
        assert tagged.one().annotation == 7
        assert tagged.value.one() == S.yes
        assert program.answers(S.tagged_call(V.value), under=counting).one() == 1

        ordinary = program.answers(S.ordinary_call(), under=ranked).one()
        assert ordinary.value == S.ordinary


def test_under_answers_defers_its_tagged_route_probe_until_pull(metta, monkeypatch):
    """Selecting a carrier does not make Answers construction eager."""
    module = importlib.import_module("metta.algebra")
    probes = 0
    original = module.has_tagged_program

    def observed(space, query):
        nonlocal probes
        probes += 1
        return original(space, query)

    monkeypatch.setattr(module, "has_tagged_program", observed)
    with metta._new_space() as program:
        program.run("(= (lazy-under) yes)")
        answers = program.answers(S.lazy_under(), under=ranked)
        assert probes == 0
        assert answers.one().value == S.yes
        assert probes == 1


def test_algebra_module_is_the_constructor_and_the_old_space_doors_are_retired(
    metta,
):
    """One real callable module preserves import identity and declares carriers."""
    module = importlib.import_module("metta.algebra")
    assert metta_module.algebra is module
    assert callable(module)
    declared = module(
        S.under_max_plus,
        plus=max,
        times=lambda left, right: left + right,
        zero=-100,
        one=0,
        order="descending",
    )
    assert declared.name == "under-max-plus"

    @module(zero=0, one=1, order="descending")
    class UnderDecorated:
        @staticmethod
        def plus(left, right):
            return max(left, right)

        @staticmethod
        def times(left, right):
            return left + right

    assert UnderDecorated.name == "UnderDecorated"
    with metta._new_space() as program:
        program.add_tagged_fact(1, S.option(S.low))
        program.add_tagged_fact(9, S.option(S.high))
        program.add_tagged_fact(2, S.base(S.x))
        program.add_tagged_rule(3, S.derived(S.x), S.base(S.x))
        answers = program.match(S.option(V.value), under=declared)
        assert answers.value.first() == S.high
        assert program.match(S.derived(S.x), under=declared).one().annotation == 5
    assert not hasattr(metta_module, "evaluate_algebra")
    assert not hasattr(metta_module, "sample_rates")
    assert not hasattr(metta_module._space.Space, "evaluate_algebra")
    assert not hasattr(metta_module._space.Space, "sample_rates")


def test_space_sample_is_seeded_and_uses_k_vocabulary(metta):
    """Sampling is with replacement, deterministic locally, and returns k draws."""
    with metta._new_space() as costs:
        costs.add_tagged_fact(S.rate(1), S.route(S.slow))
        costs.add_tagged_fact(S.rate(3), S.route(S.fast))
        costs.add_tagged_fact(S.rate(2), S.route(S.fast))
        first = costs.sample(S.route(V.x), k=10, seed=7)
        second = costs.sample(S.route(V.x), k=10, seed=7)
        assert first == second
        assert len(first) == 10
        assert {str(answer) for answer in first} <= {"(route slow)", "(route fast)"}


@pytest.mark.parametrize("carrier", [counting, tropical, prov, ranked, metta_module.prob])
def test_requested_carrier_spellings_are_declared(carrier):
    """The exact bare names from the algebra-tower cell are carrier objects."""
    assert carrier.name in {"counting", "tropical", "prov", "ranked", "prob"}


def test_semiring_vocabulary_members_are_carrier_spellings(metta):
    """The generated catalog enum reaches the same resolver as bare objects."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.a))
        assert facts.match(S.item(V.x), under=Semiring.counting).one() == 2
