"""Purpose: exercise carrier and demand at public evaluator crossings.

Guarantees:
  - callbacks observe the requested carrier and providers receive only licensed
    bounds [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context.py -n 0; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
"""

from __future__ import annotations

import pytest

import metta as m
from metta import Answer, Atom, S, V, algebra, prov, ranked, tropical
from metta._declare import declarations as _space_declarations
from metta._errors.errors import EngineError
from metta.algebra import AlgebraEvaluationError
from metta.foreign import SpaceProvider


@pytest.fixture
def context_space(metta, request):
    """Use distinct catalog subjects because anonymous names are pooled."""
    space = metta._at(f"&{request.node.name}")
    try:
        yield space
    finally:
        space.drop()


@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("annotated", [False, True])
@pytest.mark.parametrize("door", ["match", "answers", "eval"])
def test_tagged_callbacks_observe_the_requested_carrier(
    context_space, inferences, annotated, door
):
    """Explicit selection survives arithmetic and guarded engine crossings."""
    with context_space as space:
        seen = []
        carrier_name = f"crossing-observed-{door}-{annotated}-{inferences}"
        recording = False

        def observe(operation):
            seen.append((operation, m.current_algebra()))
            assert m.current_algebra() == carrier_name
            context = space.runtime.once(
                "metta_evaluation_context(evaluation_context(A, L, D))"
            )
            assert (context["A"], context["L"], context["D"]) == (
                carrier_name, 2 if door == "match" else 0, "descending",
            )

        def combine(left: int, right: int) -> int:
            if recording:
                observe("combine")
            return max(left, right)

        def extend(left: int, right: int) -> int:
            if recording:
                observe("extend")
            return (left * right) % 16

        def guard(value: Atom) -> bool:
            observe("where")
            return value == S.a

        space.op(combine, name="crossing-combine", effect="pureStructural")
        space.op(extend, name="crossing-extend", effect="pureStructural")
        space.op(guard, name="crossing-guard", effect="readOnlyLookup")
        # The certificate covers every runtime tag. Multiplication modulo 16
        # closes this complete finite carrier and preserves the observed
        # products 2 * 5 = 10 and 3 * 5 = 15.
        space.algebra(
            carrier_name, combine="crossing-combine",
            extend="crossing-extend", zero=0, one=1,
            laws=("combine-associative",), carrier=range(16), order="descending",
        )
        space.add(
            algebra.tagged_fact(2, S.crossing_seed(S.a)),
            algebra.tagged_fact(3, S.crossing_seed(S.a)),
            algebra.tagged_rule(5, S.crossing_result(V.x), S.crossing_seed(V.x)),
        )
        if annotated:
            space.annotations("tropical")
        recording = True
        options = {"under": carrier_name, "inferences": inferences}
        if door == "match":
            options["where"] = S.crossing_guard(V.x)
            options["limit"] = 2
        with space:
            answers = list(getattr(space, door)(S.crossing_result(V.x), **options))
            assert [answer.annotation for answer in answers] == [15]
            assert {operation for operation, _ in seen} == (
                {"combine", "extend", "where"}
                if door == "match" else {"combine", "extend"}
            )
            assert m.current_algebra() == ("tropical" if annotated else None)


class _OrderedScores(SpaceProvider):
    """Keep provider demand and complete ranked answers observable."""

    def __init__(self):
        self.limits = []

    def atoms(self):
        return iter(())

    def match(self, _pattern, *, limit=None):
        self.limits.append(limit)
        for value, score in [(S.best, 9), (S.middle, 4), (S.low, 1)][:limit]:
            yield Answer(value=S.context_score(value), k=score)


@pytest.mark.parametrize("door", ["limit", "slice", "top"])
def test_ranked_demand_reaches_the_provider_through_each_door(metta, door):
    """Explicit match limits offer the same bound as a slice and engine top."""
    provider = _OrderedScores()
    name = f"&context-ranked-demand-{door}"
    _space_declarations._register_space(metta, provider, name)
    try:
        scores = metta._at(name)
        scores.annotations("ranked")
        scores.handles("(context-score $x)", "Exact")
        scores.emits("best-first")
        if door == "limit":
            answers = scores.match(S.context_score(V.x), under=ranked, limit=2).x
        elif door == "slice":
            answers = scores.match(S.context_score(V.x), under=ranked)[:2].x
        else:
            answers = scores.eval(
                f"(top 2 (match {name} (context-score $x) $x))"
            )
        assert list(answers) == [S.best, S.middle]
        assert provider.limits == [2]
    finally:
        _space_declarations._unregister_space(metta, name)


@pytest.mark.parametrize("door", ["limit", "slice"])
@pytest.mark.parametrize("barrier", ["guard", "join", "mismatch", "partial", "no-emits"])
def test_ranked_demand_stays_above_an_unsafe_provider_crossing(metta, door, barrier):
    """A bound cannot discard candidates before filtering, joining, or sorting."""
    provider = _OrderedScores()
    name = f"&context-demand-barrier-{door}-{barrier}"
    _space_declarations._register_space(metta, provider, name)
    try:
        scores = metta._at(name)
        scores.annotations("ranked")
        scores.handles("(context-score $x)", "Partial" if barrier == "partial" else "Exact")
        if barrier != "no-emits":
            scores.emits("best-first")
        patterns = (S.context_score(V.x),)
        options = {"under": tropical if barrier == "mismatch" else ranked}
        if barrier == "guard":
            options["where"] = S["=="](V.x, S.low)
        elif barrier == "join":
            patterns += (S.context_score(V.x),)
        if door == "limit":
            answers = scores.match(*patterns, limit=1, **options)
        else:
            answers = scores.match(*patterns, **options)[:1]
        assert list(answers.x) == [S.low if barrier in {"guard", "mismatch"} else S.best]
        assert provider.limits and all(limit is None for limit in provider.limits)
    finally:
        _space_declarations._unregister_space(metta, name)


@pytest.mark.parametrize("local_conflict", [False, True])
def test_a_retained_derivation_pairs_with_the_explicit_algebra_object(metta, local_conflict):
    """An object retains its operations even beside another declaration's name."""
    with metta._new_space() as owner, metta._new_space() as source:
        seen = []
        carrier_name = f"context-direct-pair-{local_conflict}"

        def times(left: int, right: int) -> int:
            seen.append(m.current_algebra())
            assert m.current_algebra() == carrier_name
            return left * right

        with owner:
            carrier = algebra(
                carrier_name, plus=lambda left, right: left + right,
                times=times, zero=0, one=1,
            )
        source.add(
            algebra.tagged_fact(2, S.context_base),
            algebra.tagged_rule(3, S.context_derived, S.context_base),
        )
        answer = source.match(S.context_derived, under=prov).one()
        if local_conflict:
            source.algebra(carrier_name, combine="+", extend="+", zero=0, one=0)
        source.remove(
            algebra.tagged_fact(2, S.context_base),
            algebra.tagged_rule(3, S.context_derived, S.context_base),
        )
        with source:
            assert answer.under(carrier).annotation == 6
            assert seen and set(seen) == {carrier_name}
            assert m.current_algebra() is None
        if local_conflict:
            assert answer.under(carrier_name).annotation == 5


def test_one_host_operation_serves_two_carriers_and_restores_nested_scope(metta):
    """The active carrier controls one host operation through nested evaluation."""
    with metta._new_space() as space:
        seen = []

        def extend(left: int, right: int) -> int:
            name = m.current_algebra()
            seen.append(name)
            if name == "context-product":
                with m.under("context-sum"):
                    nested = space.match(S.context_derived, under="context-sum").one()
                    assert nested.annotation == 5
                assert m.current_algebra() == "context-product"
                return left * right
            assert name == "context-sum"
            return left + right

        space.op(extend, name="context-shared-extend", effect="pureStructural")
        space.algebra("context-product", combine="+", extend="context-shared-extend", zero=0, one=1)
        space.algebra("context-sum", combine="+", extend="context-shared-extend", zero=0, one=0)
        space.add(
            algebra.tagged_fact(2, S.context_base),
            algebra.tagged_rule(3, S.context_derived, S.context_base),
        )
        with space, m.under(tropical):
            assert space.match(S.context_derived, under="context-product").one().annotation == 6
            assert m.current_algebra() == "tropical"
        assert set(seen) == {"context-product", "context-sum"}


@pytest.mark.parametrize("inferences", [None, 1_000_000])
def test_callback_failure_restores_the_enclosing_carrier(context_space, inferences):
    """Exceptional crossings restore the caller before another evaluation."""
    seen = []

    def extend(_left: int, _right: int) -> int:
        seen.append(m.current_algebra())
        message = "context callback failure"
        raise RuntimeError(message)

    space = context_space
    space.op(extend, name="context-failing-extend", effect="pureStructural")
    space.algebra("context-failure", combine="+", extend="context-failing-extend", zero=0, one=1)
    space.add(
        algebra.tagged_fact(2, S.context_base),
        algebra.tagged_rule(3, S.context_derived, S.context_base),
    )
    with space, m.under(tropical):
        with pytest.raises(EngineError, match="context callback failure"):
            space.match(S.context_derived, under="context-failure", inferences=inferences).one()
        assert seen == ["context-failure"]
        assert m.current_algebra() == "tropical"
        assert space.match(S.context_base, under=ranked).one().annotation == 2
        assert m.current_algebra() == "tropical"


def test_a_failed_match_reports_the_selected_carrier_name(context_space):
    """Passing the descriptor internally preserves the public refusal message."""
    space = context_space
    space.add(
        algebra.tagged_fact(1, S.context_loop),
        algebra.tagged_rule(1, S.context_loop, S.context_loop),
    )
    with pytest.raises(AlgebraEvaluationError) as failure:
        space.match(S.context_loop, under=ranked).one()
    assert str(failure.value) == "algebra_derivation_did_not_reach_fixpoint(ranked, rounds=64)"
