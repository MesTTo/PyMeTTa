"""Purpose: pin algebra carriers on match, call, scope, sampling, and answers.

Guarantees:
  - the visibility preset shares the native finite carrier and rejects other
    symbols [tested: test_visibility_operations_share_the_native_carrier;
    commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].
  - counting uses the engine aggregate for both query and call bags, including
    duplicate derivations [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    test_counting_counts_duplicate_call_answers_inside_the_engine,
    test_counting_inference_growth_is_linear_when_answers_grow_in_depth;
    commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427]
  - ordered carriers determine answer order before an Answers slice selects
    its prefix, and a pristine bounded slice reaches only a provider licensed
    by Exact, matching ordered annotations, and best-first emission [tested:
    test_ranked_and_tropical_slices_are_stable_best_prefixes,
    test_pristine_ranked_slice_pushes_only_the_licensed_provider_bound;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
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
  - tagged counts and ordinary matches share one positive-limit contract
    [tested: test_tagged_count_and_match_refuse_zero_with_the_same_message;
    commit=61e107a8105a5cdaea164f615812a684b12d8fe3]
  - custom algebra declarations are visible only to their owning context and
    distinct contexts may reuse one algebra name [tested:
    test_custom_algebras_are_context_owned; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - the module-level algebra constructor follows the active space context
    [tested: test_algebra_module_constructor_targets_the_ambient_space;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
  - counting answers share TaggedAnswer's value, annotation, explanation, and
    reinterpretation protocol [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    test_counting_counts_duplicate_call_answers_inside_the_engine;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
  - current_algebra observes explicit, scoped, and context-declared carriers
    in precedence order while leaving an undeclared context as None [tested:
    test_current_algebra_follows_each_selection_layer; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - the generated AlgebraLaw vocabulary and catalog alias claims drive public
    declaration expansion and unknown-law remedies [tested:
    test_algebra_law_vocabulary_drives_aliases_and_unknown_refusals;
    commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]
  - a law list of equations expands without reading the alias claims, and
    answers what the reading path answers [tested:
    test_equational_law_names_read_no_catalog; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

import metta as metta_module
import metta.aio as _aio_surface
from metta import Answer, S, V, counting, prob, prov, ranked, tropical
from metta._declare import declarations as _space_declarations
from metta.algebra import AlgebraDeclarationError
from metta.foreign import SpaceProvider
from metta.vocabularies import AlgebraLaw, Semiring


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

        monkeypatch.setattr("metta._spaces.cursor.Cursor", cursor_must_not_open)
        counted = facts.match(S.edge(S.a, V.x), under=counting)
        with facts.stats() as measured:
            answer = counted.one()

        assert answer.value == ()
        assert answer.tag == metta_module.G(3)
        assert answer.annotation == 3
        assert answer.why().answer == ()
        assert answer.under(prob).annotation == 3
        assert measured.inferences > 0
        assert len(counted._cache) == 1
        assert facts.match(S.absent(V.x), under=counting).one().annotation == 0


def test_counting_counts_duplicate_call_answers_inside_the_engine(metta):
    """Equal answers from distinct equations remain two bag derivations."""
    with metta._new_space() as program:
        program.run(
            "(= (under-call) same)\n"
            "(= (under-call) same)\n"
            "(= (under-call) other)"
        )
        with program.stats() as measured:
            answer = program.answers(S.under_call(), under=counting).one()
        assert answer.value == ()
        assert answer.annotation == 3
        assert measured.inferences > 0


def test_tagged_count_and_match_refuse_zero_with_the_same_message(metta):
    """Zero cannot cross into either engine query as the unbounded sentinel."""
    query = S.limit_contract(V.value)
    module = importlib.import_module("metta.algebra")

    with pytest.raises(ValueError) as match_error:
        metta.match(query, limit=0)
    with pytest.raises(ValueError) as tagged_error:
        module.count_tagged(metta, query, limit=0)

    expected = "limit must be positive, got 0"
    assert str(match_error.value) == expected
    assert str(tagged_error.value) == expected


def test_counting_inference_growth_is_linear_when_answers_grow_in_depth(metta):
    """Doubling deep answers stays subquadratic inside the count query."""
    # An outer stats window can drain an unrelated abandoned world's release.
    # Observe the query reached by the public door, as the nominal-subtyping
    # test observes its evaluator. The wrapper and its counter leave together.
    metta.runtime.must(
        "use_module(library(prolog_wrap)),"
        "nb_setval(counting_test_cost,0),"
        "wrap_predicate(user:metta_py_query_count_under(_Space,_Patterns,_Guard,"
        "_Names,_Limit,_Algebra,_Count),counting_test_cost,_Original,"
        "(metta_py_work(_Before),call(_Original),metta_py_work(_After),"
        "_Used is _After-_Before,nb_setval(counting_test_cost,_Used)))"
    )

    def measured(size):
        with metta._new_space() as facts:
            value = S.Z
            atoms = []
            for _ in range(size):
                atoms.append(S.num(value))
                value = S.S(value)
            facts.add(*atoms)
            assert (
                facts.match(S.num(V.value), under=counting).one().annotation
                == size
            )
            return metta.runtime.must("nb_getval(counting_test_cost, Cost)")["Cost"]

    try:
        shallow = measured(128)
        deep = measured(256)
        assert deep < 3 * shallow
    finally:
        metta.runtime.must(
            "unwrap_predicate(user:metta_py_query_count_under/7,counting_test_cost),"
            "nb_delete(counting_test_cost)"
        )


def test_scoped_under_is_task_local_and_explicit_under_wins(metta):
    """Nested scopes restore, while a per-ask carrier outranks the scope."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.b))
        facts.run("(= (scoped-call) same)\n(= (scoped-call) same)")
        with metta_module_under(counting):
            assert facts.match(S.item(V.x)).one().annotation == 2
            assert facts.fn.scoped_call().one().annotation == 2
            with metta_module_under(tropical):
                assert facts.match(S.item(V.x), under=counting).one().annotation == 2
            assert facts.match(S.item(V.x)).one().annotation == 2
        assert [str(row.x) for row in facts.match(S.item(V.x))] == ["a", "b"]


def test_scoped_under_crosses_the_async_worker_context(metta):
    """The copied ContextVar reaches AsyncMeTTa's owning engine worker."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.b))

        async def ask():
            async with _aio_surface.AsyncMeTTa(metta=facts) as worker:
                with metta_module_under(counting):
                    counted = await worker.match(S.item(V.x))
                return counted.one().annotation

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


def test_current_algebra_follows_each_selection_layer(metta):
    """One observer follows the same precedence as an evaluating query."""
    with metta._new_space() as first, metta._new_space() as second:
        with first:
            assert metta_module.current_algebra() is None

        first.annotations("ranked")
        second.annotations("tropical")
        with first:
            assert metta_module.current_algebra() == "ranked"
            with metta_module.under(counting):
                assert metta_module.current_algebra() == "counting"
        with second:
            assert metta_module.current_algebra() == "tropical"

        def inspect_algebra() -> str:
            return metta_module.current_algebra() or "none"

        first.op(
            inspect_algebra,
            name="inspect-algebra",
            effect="readOnlyLookup",
        )
        with metta_module.under(counting):
            answer = first.answers(S.inspect_algebra(), under=prov).one()
        assert answer.value == metta_module.G("prov")


def metta_module_under(carrier):
    """Keep the exact public spelling visible in the test body."""
    return metta_module.under(carrier)


def test_ranked_and_tropical_slices_are_stable_best_prefixes(metta):
    """Descending rank and ascending cost both preserve emission-order ties."""
    rows = [(S.low, 1), (S.best_a, 9), (S.best_b, 9), (S.middle, 4)]
    provider = _ScoredRows(rows)
    _space_declarations._register_space(metta, provider, "&under-ranked")
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
    _space_declarations._register_space(metta, duplicates, "&under-ranked-duplicates")
    repeated = metta._at("&under-ranked-duplicates")
    assert len(list(repeated.match(S.score(V.x), under=ranked))) == 2

    def scored_call(_query):
        for value, annotation in rows:
            yield Answer(value=value, k=annotation)

    metta.op(scored_call, name="under-scored-call", effect="nondeterministicReadOnly")
    with metta._new_space() as program:
        best = program.answers(S.under_scored_call(S.query), under=ranked)[:2]
        assert [answer.value for answer in best] == [S.best_a, S.best_b]


def test_pristine_ranked_slice_pushes_only_the_licensed_provider_bound(metta):
    """The slice reopens only a repeatable source whose declared order it can trust."""
    class BestFirstRows(SpaceProvider):
        def __init__(self):
            self.rows = [(S.best, 9), (S.middle, 4), (S.low, 1)]
            self.limits = []

        def atoms(self):
            return iter(())

        def match(self, pattern, *, limit=None):  # noqa: ARG002 -- the provider protocol requires the pattern argument
            self.limits.append(limit)
            rows = self.rows if limit is None else self.rows[:limit]
            for value, annotation in rows:
                yield Answer(value=S.score(value), k=annotation)

    provider = BestFirstRows()
    _space_declarations._register_space(metta, provider, "&slice-ranked")
    scores = metta._at("&slice-ranked")
    scores.annotations("ranked")
    scores.handles("(score $x)", "Exact")
    scores.emits("best-first")

    all_answers = scores.match(S.score(V.x), under=ranked)
    first_two = all_answers[:2]
    assert provider.limits == []
    assert [str(value) for value in first_two.x] == ["best", "middle"]
    assert provider.limits == [2]
    assert [str(value) for value in all_answers.x] == ["best", "middle", "low"]
    assert provider.limits == [2, None]

    provider.limits.clear()
    assert [
        str(value)
        for value in scores.match(S.score(V.x), under=tropical)[:1].x
    ] == ["low"]
    assert provider.limits == [None]

    no_order_promise = BestFirstRows()
    _space_declarations._register_space(metta, no_order_promise, "&slice-no-emits")
    unpromised = metta._at("&slice-no-emits")
    unpromised.annotations("ranked")
    unpromised.handles("(score $x)", "Exact")
    assert [
        str(value)
        for value in unpromised.match(S.score(V.x), under=ranked)[:1].x
    ] == ["best"]
    assert no_order_promise.limits == [None]

    inexact = BestFirstRows()
    _space_declarations._register_space(metta, inexact, "&slice-inexact")
    inexact_space = metta._at("&slice-inexact")
    inexact_space.annotations("ranked")
    inexact_space.handles("(score $x)", "Partial")
    inexact_space.emits("best-first")
    assert [
        str(value)
        for value in inexact_space.match(S.score(V.x), under=ranked)[:1].x
    ] == ["best"]
    assert inexact.limits == [None]


def test_provenance_retains_a_derivation_for_no_requery_reinterpretation(metta):
    """why/under consume the captured carrier tree rather than the provider."""
    provider = _ScoredRows([("rain", S.src(S.weather_db))])
    _space_declarations._register_space(metta, provider, "&under-prov")
    answer = metta._at("&under-prov").match(S.score(V.x), under=prov).first()

    assert "weather-db" in answer.why().render()
    assert answer.under(counting).annotation == 1
    assert provider.asks == 1


def test_tagged_derivations_flow_through_match_and_reinterpret_without_requery(
    metta,
):
    """The former evaluate_algebra capability lives behind match(under=)."""
    with metta._new_space() as program:
        program.algebra(
            "under-product",
            combine="+",
            extend="*",
            zero=0,
            one=1,
        )
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
        ).one().annotation == 1


def test_tagged_call_answers_use_the_carrier_without_hijacking_other_calls(metta):
    """Tagged routing is query-specific and both call kinds keep their values."""
    with metta._new_space() as program:
        program.algebra(
            "under-call-product",
            combine="+",
            extend="*",
            zero=0,
            one=1,
        )
        program.add_tagged_fact(7, S.tagged_call(S.yes))
        program.run("(= (ordinary-call) ordinary)")

        tagged = program.answers(
            S.tagged_call(V.value), under="under-call-product"
        )
        assert tagged.one().annotation == 7
        assert tagged.value.one() == S.yes
        assert (
            program.answers(S.tagged_call(V.value), under=counting)
            .one()
            .annotation
            == 1
        )

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
        program.algebra(
            declared.name,
            combine=declared.combine,
            extend=declared.extend,
            zero=declared.zero,
            one=declared.one,
            order=declared.order,
        )
        program.add_tagged_fact(1, S.option(S.low))
        program.add_tagged_fact(9, S.option(S.high))
        program.add_tagged_fact(2, S.base(S.x))
        program.add_tagged_rule(3, S.derived(S.x), S.base(S.x))
        answers = program.match(S.option(V.value), under=declared)
        assert answers.value.first() == S.high
        assert program.match(S.derived(S.x), under=declared).one().annotation == 5
    assert not hasattr(metta_module, "evaluate_algebra")
    assert not hasattr(metta_module, "sample_rates")
    assert not hasattr(metta_module.Space, "evaluate_algebra")
    assert not hasattr(metta_module.Space, "sample_rates")


def test_custom_algebras_are_context_owned(metta):
    """Algebra rows and annotations use the same context lifetime key."""
    algebra_module = importlib.import_module("metta.algebra")
    with metta._new_space() as left, metta._new_space() as right:
        left.algebra(
            "same-local-name", combine="+", extend="*", zero=0, one=1
        )
        assert algebra_module.require(left, "same-local-name").one == metta_module.G(1)
        with pytest.raises(
            algebra_module.AlgebraDeclarationError,
            match="algebra_not_declared",
        ):
            algebra_module.require(right, "same-local-name")
        with metta_module.MeTTa() as isolated:
            with pytest.raises(
                algebra_module.AlgebraDeclarationError,
                match="algebra_not_declared",
            ):
                algebra_module.require(isolated.self, "same-local-name")
            assert algebra_module.require(isolated.self, "ranked").name == "ranked"

        right.algebra(
            "same-local-name", combine="+", extend="*", zero=0, one=9
        )
        assert algebra_module.require(right, "same-local-name").one == metta_module.G(9)
        assert algebra_module.require(left, "same-local-name").one == metta_module.G(1)
        assert str(left.annotations("same-local-name")) == (
            f"(annotations {left.name} same-local-name)"
        )
        assert str(right.annotations("same-local-name")) == (
            f"(annotations {right.name} same-local-name)"
        )
        assert left.runtime.must(
            "metta_algebra_one(Ctx, One)", Ctx=left.name
        )["One"] == 1
        assert right.runtime.must(
            "metta_algebra_one(Ctx, One)", Ctx=right.name
        )["One"] == 9


def test_algebra_module_constructor_targets_the_ambient_space(metta):
    """The implicit constructor receiver is the current space, not ``&self``."""
    algebra_module = importlib.import_module("metta.algebra")
    with metta._new_space() as program:
        with program:
            declared = algebra_module(
                "ambient-product",
                plus=lambda left, right: left + right,
                times=lambda left, right: left * right,
                zero=0,
                one=1,
            )

        assert algebra_module.require(program, "ambient-product") == declared
        program.add_tagged_fact(3, S.ambient(S.value))
        assert (
            program.match(S.ambient(S.value), under=declared).one().annotation
            == 3
        )

    with pytest.raises(
        algebra_module.AlgebraDeclarationError,
        match="algebra_not_declared",
    ):
        algebra_module.require(metta, "ambient-product")


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


@pytest.mark.parametrize(
    "carrier",
    [
        metta_module.bool,
        metta_module.bag,
        counting,
        metta_module.set,
        ranked,
        tropical,
        metta_module.prob,
        prov,
        metta_module.budget,
        metta_module.amplitude,
    ],
)
def test_requested_carrier_spellings_are_declared(carrier):
    """The exact bare names from the algebra-tower cell are carrier objects."""
    assert carrier.name in {member.value for member in Semiring}


def test_every_shipped_semiring_has_one_root_object_in_catalog_order():
    """Each generated Semiring member is a root carrier object of that name.

    ch20's test_every_algebra_the_catalog_defines_is_one_its_vocabulary_admits
    compares the presets against the enum as sets. What that cannot see is the
    third roster, `metta.<name>`, the objects a Python annotation reaches:
    five of the ten were exported and five were reachable only as strings, so
    `metta.budget` raised AttributeError for a carrier that already answered
    `under="budget"`. The order is pinned here too, because the enum is
    generated from the catalog row and the presets are written beside it.
    """
    algebra_module = importlib.import_module("metta.algebra")
    names = tuple(member.value for member in Semiring)
    assert names == tuple(algebra_module._PRESETS)
    assert all(getattr(metta_module, name).name == name for name in names)


@pytest.mark.parametrize("left", (S.INTERNAL, S.PUBLIC))
@pytest.mark.parametrize("right", (S.INTERNAL, S.PUBLIC))
def test_visibility_operations_share_the_native_carrier(metta, left, right):
    """The Python preset and native grades use the same two-element lattice."""
    from metta.algebra import AlgebraOperationError, visibility

    assert visibility.carrier == (S.INTERNAL, S.PUBLIC)
    assert visibility.combine_values(metta, left, right) == (
        S.PUBLIC if S.PUBLIC in (left, right) else S.INTERNAL
    )
    assert visibility.extend_values(metta, left, right) == (
        S.INTERNAL if S.INTERNAL in (left, right) else S.PUBLIC
    )
    with pytest.raises(AlgebraOperationError):
        visibility.combine_values(metta, left, S.outside)


def test_algebra_law_vocabulary_drives_aliases_and_unknown_refusals(metta):
    """Alias expansion and the refusal remedy read the catalog vocabulary."""
    module = importlib.import_module("metta.algebra")
    expected_aliases = {
        "associative": ("combine-associative", "extend-associative"),
        "commutative": ("combine-commutative",),
        "distributive": ("left-distributive", "right-distributive"),
        "distributes-over": ("left-distributive", "right-distributive"),
        "idempotent": ("combine-idempotent",),
        "identity": ("combine-zero-identity", "extend-one-identity"),
        "contraction": ("contraction",),
    }
    assert module._catalog_law_aliases(metta) == expected_aliases

    metta.algebra(
        "catalog-alias-laws",
        combine="max",
        extend="min",
        zero=0,
        one=1,
        laws=("associative",),
        carrier=(0, 1),
    )
    assert module.require(metta, "catalog-alias-laws").laws == frozenset(
        {"combine-associative", "extend-associative"}
    )

    with pytest.raises(AlgebraDeclarationError) as refusal:
        metta.algebra(
            "catalog-unknown-law",
            combine="max",
            extend="min",
            zero=0,
            one=1,
            laws=("transitive",),
        )
    accepted = ", ".join(member.value for member in AlgebraLaw)
    assert str(refusal.value) == (
        "algebra_law_unknown(['transitive']); accepted laws are " + accepted
    )


def test_equational_law_names_read_no_catalog(metta, monkeypatch):
    """Equations answer without the catalog read an alias needs, and agree."""
    module = importlib.import_module("metta.algebra")
    space_module = importlib.import_module("metta._faces.space")
    original = space_module.Space.match
    asked: list[str] = []

    def counting_match(self, *args, **kwargs):
        asked.append(str(self.name))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(space_module.Space, "match", counting_match)
    equations = ("combine-associative", "extend-associative")
    assert module._canonical_laws(metta, equations) == frozenset(equations)
    assert asked == []
    # One pattern match for the alias rows, never a walk of every catalog atom.
    assert module._canonical_laws(metta, ("associative",)) == frozenset(equations)
    assert asked == ["&metta"]


def test_semiring_vocabulary_members_are_carrier_spellings(metta):
    """The generated catalog enum reaches the same resolver as bare objects."""
    with metta._new_space() as facts:
        facts.add(S.item(S.a), S.item(S.a))
        assert (
            facts.match(S.item(V.x), under=Semiring.counting).one().annotation == 2
        )


def test_a_streamed_algebra_answers_what_a_matched_one_answers(metta):
    """One word, one meaning, whichever door you hold.

    stream(under=) reached the cursor's raw protocol at first, a bare row
    with a separate .annotation, where match(under=) answers the folded
    algebra value; the same word meant two things for one afternoon. It
    answers the same TaggedAnswer now, and 'counting' is refused by name
    rather than answered differently, a fold over the whole answer set being
    the thing a cursor exists not to have [measured 2026-08-31].
    """
    space = metta._at("&self")
    space.add(S.streamed(S.a, 1), S.streamed(S.b, 9))
    for carrier in ("ranked", "tropical", "prov"):
        matched = list(space.match(S.streamed(V.x, V.n), under=carrier))
        with space.stream(S.streamed(V.x, V.n), under=carrier) as cursor:
            assert list(cursor) == matched
    counted = list(space.match(S.streamed(V.x, V.n), under="counting"))
    assert [answer.annotation for answer in counted] == [2]
    with pytest.raises(TypeError, match="nothing to stream"):
        space.stream(S.streamed(V.x, V.n), under="counting")


def test_a_scoped_carrier_reaches_every_evaluating_door(metta):
    """A scope that reaches two doors of three is a scope that lies.

    match() and answers() both honoured a surrounding metta.under(carrier);
    eval() ignored it in silence, so a block written under a carrier quietly
    meant nothing for one of the three doors inside it, and there was no
    signal at all [measured 2026-08-31]. eval() carries answers()' three
    parameters now, being that door materialised.
    """
    space = metta._at("&self")
    space.run("(= (scoped-path a) b) (= (scoped-path a) c)")
    assert space.eval(S["scoped-path"](S.a)) == [S.b, S.c]
    assert [
        answer.annotation
        for answer in space.eval(S["scoped-path"](S.a), under="counting")
    ] == [2]
    with metta_module.under("counting"):
        assert [
            answer.annotation for answer in space.eval(S["scoped-path"](S.a))
        ] == [2]
        assert [
            answer.annotation for answer in space.answers(S["scoped-path"](S.a))
        ] == [2]
    # And the scope ends where the block ends.
    assert space.eval(S["scoped-path"](S.a)) == [S.b, S.c]
