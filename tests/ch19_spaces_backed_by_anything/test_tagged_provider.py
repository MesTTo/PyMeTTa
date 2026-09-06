"""Purpose: require tagged premises to use their provider's ordinary match door.

Guarantees:
  - typed provider tags retain the selected declaration and share the ask's
    context and remaining resource budget [tested:
    test_provider_conclusions_check_the_explicit_typed_carrier,
    test_provider_carrier_predicate_shares_the_source_budget; commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - direct and derived provider queries retain the same carrier, demand and
    order without clipping guarded candidates [tested:
    test_provider_premises_retain_the_direct_match_context; commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - provider annotations, duplicate occurrences, failures and refreshed reads
    remain visible through native tagged rules [tested: this module;
    commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - an opaque mutable provider k keeps the same host object in the derived
    prov expression and retained source trace [tested:
    test_grounded_provider_annotation_retains_host_object_identity;
    commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
"""

from __future__ import annotations

import pytest

from metta import (
    Answer,
    G,
    S,
    V,
    Variable,
    current_algebra,
    prob,
    prov,
    ranked,
    tropical,
    under,
    wire,
)
from metta import space as make_space
from metta.algebra import AlgebraOperationError, LinearEvidenceError, evaluate, require, tagged_rule
from metta.errors import EngineError, InferenceLimitError, TimeLimitError
from metta.foreign import SpaceProvider

pytestmark = pytest.mark.usefixtures("metta")


class WeightedRules(SpaceProvider):
    """Stored rules and weighted facts available only through matching."""

    def __init__(self, rules, rows):
        """Keep declaration atoms separate from weighted match rows."""
        self.rules = rules
        self.rows = rows
        self.asked = []

    def atoms(self):
        """Expose rule declarations without inventing tags for enumeration."""
        return iter(self.rules)

    def match(self, pattern):
        """Offer every weighted candidate for engine-side matching."""
        self.asked.append(pattern)
        for value, weight in self.rows:
            yield Answer(value=value, k=weight)


@pytest.mark.parametrize("carrier,coefficient,expected", [
    ("prov", 1, S.times(1, 0.9)),
    ("prob", 1, G(0.9)),
    ("bag", 1, G(0.9)),
    ("ranked", 1, G(0.9)),
    ("set", 1, G(0.9)),
    ("tropical", 0, G(0.9)),
    ("budget", 0, G(0.9)),
])
def test_tagged_premise_keeps_the_direct_provider_annotation(
    carrier, coefficient, expected,
):
    """The engine filters over-approximate provider rows on both doors."""
    provider = WeightedRules(
        [tagged_rule(coefficient, S.bad(V.x), S.err(V.x))],
        [(S.unrelated(S.x), 99), (S.err(S.x), 0.9)],
    )
    with make_space(backing=provider) as space:
        direct = space.match(S.err(S.x), under=carrier).one()
        derived = space.match(S.bad(S.x), under=carrier).one()
        assert direct.annotation == 0.9
        assert derived.value == S.bad(S.x)
        assert derived.tag == expected
        assert not derived.plan[1].applied
        assert "0.9" in derived.why().render()


def test_provider_proofs_reinterpret_without_requery_and_refresh_on_next_ask():
    """A retained source keeps k while each new evaluation reads fresh data."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.x), 0.9)],
    )
    with make_space(backing=provider) as space:
        answer = space.match(S.bad(S.x), under=prov).one()
        asks = len(provider.asked)
        space.algebra(
            "provider-reinterpret", combine="max", extend="*", zero=0, one=1,
        )
        assert answer.under("provider-reinterpret").annotation == 0.9
        assert answer.under(prob).annotation == 0.9
        assert len(provider.asked) == asks
        provider.rows = [(S.err(S.x), 0.3)]
        assert space.match(S.bad(S.x), under=prob).one().annotation == 0.3
        assert answer.under(prob).annotation == 0.9


def test_provider_duplicate_premises_keep_four_proofs_and_one_source_bag():
    """Repeated premises reuse source identities while retaining the bag."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x), S.err(V.x))],
        [(S.err(S.x), 2), (S.err(S.x), 2)],
    )
    with make_space(backing=provider) as space:
        answer = space.match(S.bad(S.x), under=prob).one()
        assert answer.annotation == 16
        traces = answer.why().alternatives
        assert len(traces) == 4
        assert len(answer.tokens) == 2
        assert len(provider.asked) == 3  # unbound premise, bound premise, conclusion
        assert space.match(S.bad(S.x), under="counting").one().annotation == 4


def test_provider_absence_stays_empty_in_tagged_derivations():
    """An empty provider is absence rather than the rule's own coefficient."""
    provider = WeightedRules([tagged_rule(1, S.bad(V.x), S.err(V.x))], [])
    with make_space(backing=provider) as space:
        assert list(space.match(S.bad(S.x), under=prob)) == []
        assert space.match(S.bad(S.x), under="counting").one().annotation == 0


def test_provider_integer_rows_do_not_claim_static_demand_certification():
    """Live providers have no whole-program scalar or failure certificate."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.x), 2)],
    )
    with make_space(backing=provider) as space:
        result = evaluate(space, S.bad(S.x), algebra="bag")
        assert result.answers[0].annotation == 2
        assert not result.plan[1].applied


def test_tagged_provider_matches_preserve_annotation_refusals():
    """Bool cannot silently discard a foreign coefficient on either door."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))], [(S.err(S.x), 0.9)]
    )
    with make_space(backing=provider) as space:
        for pattern in (S.err(S.x), S.bad(S.x)):
            with pytest.raises(EngineError, match="declares no semiring"):
                space.match(pattern, under="bool").one()


def test_tagged_provider_sources_and_derived_conclusions_are_both_answers():
    """A tagged head must not hide an ordinary provider fact of that head."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.x), 0.3), (S.bad(S.x), 0.7)],
    )
    with make_space(backing=provider) as space:
        assert space.match(S.bad(S.x), under=prob).one().annotation == 1.0
        assert space.match(S.bad(S.x), under="counting").one().annotation == 2


def test_tagged_provider_linear_evidence_requires_stable_occurrence_identity():
    """Query-dependent weights cannot manufacture a second physical token."""
    class Reweighted(WeightedRules):
        def match(self, pattern):
            """The same row receives a different score for a bound query."""
            if pattern.children[0] == S.err:
                weight = 2 if isinstance(pattern.children[1], Variable) else 3
                yield Answer(value=S.err(S.x), k=weight)

    provider = Reweighted(
        [tagged_rule(1, S.bad(V.x), S.err(V.x), S.err(V.x))],
        [(S.err(S.x), 2)],
    )
    with make_space(backing=provider) as space:
        space.algebra(
            "provider-linear", combine="+", extend="*", zero=0, one=1,
            requires=("linear",),
        )
        annotation = space.annotations("provider-linear", capabilities=("linear",))
        try:
            assert space.match(S.err(V.x), under="provider-linear").one().annotation == 2
            assert space.match(S.err(S.x), under="provider-linear").one().annotation == 3
            with pytest.raises(LinearEvidenceError, match="linear_provider_occurrence_identity_missing"):
                space.match(S.bad(S.x), under="provider-linear").one()
        finally:
            make_space("&metta").remove(annotation)


def test_tagged_provider_match_uses_the_remaining_call_inference_budget():
    """Provider matching consumes the same call budget as algebra operations."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.x), 2)],
    )
    with make_space(backing=provider) as space:
        with pytest.raises(InferenceLimitError):
            space.match(S.bad(S.x), under=prob, inferences=1).one()
        assert space.match(S.bad(S.x), under=prob).one().annotation == 2


def test_provider_failures_remain_errors_in_tagged_derivations():
    """An unavailable premise source cannot masquerade as an empty proof bag."""
    class Unavailable(WeightedRules):
        def match(self, pattern):
            """Refuse this provider read before producing any candidate."""
            del pattern
            msg = "prediction source unavailable"
            raise ValueError(msg)

    provider = Unavailable([tagged_rule(1, S.bad(V.x), S.err(V.x))], [])
    with make_space(backing=provider) as space:
        for pattern in (S.err(S.x), S.bad(S.x)):
            with pytest.raises(EngineError, match="prediction source unavailable"):
                space.match(pattern, under=prob).one()


def test_grounded_provider_annotation_retains_host_object_identity():
    """Provenance keeps the live prediction object through both wire crossings."""
    prediction = {"error": 0.9}
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.x), G(prediction))],
    )
    with make_space(backing=provider) as space:
        direct = space.match(S.err(S.x), under=prov).one()
        derived = space.match(S.bad(S.x), under=prov).one()
        assert direct.annotation is prediction
        assert derived.value == S.bad(S.x)
        assert derived.tag.children[:2] == (S.times, G(1))
        assert wire.decode(derived.tag.children[2]) is prediction
        source = derived.why().alternatives[0].children[0]
        assert wire.decode(source.raw) is prediction
        asks = len(provider.asked)
        provider.rows.clear()
        prediction["error"] = 0.3
        assert wire.decode(derived.why().alternatives[0].children[0].raw) is prediction
        assert wire.decode(derived.tag.children[2])["error"] == 0.3
        assert len(provider.asked) == asks
    assert wire.decode(source.raw) is prediction


@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("annotated", [False, True])
def test_provider_premises_retain_the_direct_match_context(inferences, annotated):
    """Carry request demand without clipping candidates before the guard."""
    class Observed(WeightedRules):
        def match(self, pattern, *, limit=None):
            context = space.runtime.once(
                "metta_evaluation_context(evaluation_context(A, L, D))"
            )
            seen.append((current_algebra(), context["A"], context["L"], context["D"], limit))
            yield from super().match(pattern)

    provider = Observed(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.err(S.a), 9), (S.err(S.b), 4), (S.err(S.c), 1)],
    )
    with make_space(backing=provider) as space:
        annotation = space.annotations("tropical") if annotated else None
        try:
            with space:
                for head in (S.err, S.bad):
                    seen = []
                    answer = space.match(
                        head(V.x), under=ranked, limit=1,
                        where=S["=="](V.x, S.c), inferences=inferences,
                    ).one()
                    if head == S.err:
                        assert answer.value.x == S.c
                    else:
                        assert answer.value == S.bad(S.c)
                    assert answer.annotation == 1
                    assert seen and set(seen) == {("ranked", "ranked", 1, "descending", None)}
                    assert current_algebra() == ("tropical" if annotated else None)
        finally:
            if annotation is not None:
                make_space("&metta").remove(annotation)


@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("rejected", [False, True])
def test_typed_provider_premises_share_direct_membership_context(inferences, rejected):
    """Provider tags are checked under the same request on both match doors."""
    provider = WeightedRules(
        [tagged_rule(3, S.bad(V.x), S.err(V.x))], [(S.err(S.x), 2)],
    )
    with make_space(backing=provider) as space, space:
        observed = []
        recording = False

        def admits(value):
            if recording:
                context = space.runtime.once(
                    "metta_evaluation_context(evaluation_context(A, L, D))"
                )
                observed.append((value, current_algebra(), context["A"], context["L"], context["D"]))
            return isinstance(value, int) and not (rejected and value == 2)

        name = "provider-membership-context"
        space.algebra(name, combine="max", extend="*", zero=0, one=1,
                      type=admits, order="descending")
        recording = True
        with under(tropical):
            previous = space.runtime.once("metta_evaluation_context(Context)")
            for head in (S.err, S.bad):
                observed.clear()
                if rejected:
                    with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                        space.match(head(S.x), under=name, limit=2, inferences=inferences).one()
                else:
                    answer = space.match(head(S.x), under=name, limit=2, inferences=inferences).one()
                    assert answer.annotation == (2 if head == S.err else 6)
                assert any(value == 2 for value, *_ in observed)
                assert all(row[1:] == (name, name, 2, "descending") for row in observed)
                assert current_algebra() == "tropical"
                assert space.runtime.once("metta_evaluation_context(Context)") == previous


@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("door", ["stream", "match"])
@pytest.mark.parametrize("rejected", [False, True])
@pytest.mark.parametrize("local_type", [None, lambda value: isinstance(value, int) and value < 2],
                         ids=["unconstrained-local", "narrow-local"])
def test_provider_conclusions_check_the_explicit_typed_carrier(metta, inferences, door, rejected, local_type):
    """A local same-name row cannot replace an explicitly selected type."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))],
        [(S.bad(S.x), "outside" if rejected else 2)],
    )
    with metta._new_space() as owner, make_space(backing=provider) as space:
        name = "provider-explicit-type"
        owner.algebra(name, combine="max", extend="*", zero=0, one=1,
                      type=int, order="descending")
        declared = require(owner, name)
        space.algebra(name, combine="max", extend="*", zero=0, one=1, type=local_type)
        with space, under(tropical):
            previous = space.runtime.once("metta_evaluation_context(Context)")
            if rejected:
                with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                    list(getattr(space, door)(S.bad(S.x), under=declared, limit=2, inferences=inferences))
            else:
                answers = list(getattr(space, door)(S.bad(S.x), under=declared, limit=2, inferences=inferences))
                assert len(answers) == 1
                assert answers[0].annotation == 2
            assert current_algebra() == "tropical"
            assert space.runtime.once("metta_evaluation_context(Context)") == previous


@pytest.mark.parametrize("resource", ["inferences", "timeout"])
def test_provider_carrier_predicate_shares_the_source_budget(metta, resource):
    """A reentrant carrier check cannot escape the source crossing's quota."""
    provider = WeightedRules(
        [tagged_rule(1, S.bad(V.x), S.err(V.x))], [(S.err(S.x), 2)],
    )
    with metta._new_space() as helper, make_space(backing=provider) as space, space:
        helper.run("(= (provider-carrier-spin $n) (if (== $n 0) True (provider-carrier-spin (- $n 1))))")
        started, finished = [], []

        def admits(value):
            if value == 2:
                started.append(value)
                assert helper.runtime.apply_must(
                    "metta_py_eval_all", helper.name,
                    S.provider_carrier_spin(2_000_000).to_wire(),
                ) == [G(value=True).to_wire()]
                finished.append(value)
            return isinstance(value, int)

        name = "provider-bounded-membership"
        space.algebra(name, combine="max", extend="*", zero=0, one=1, type=admits)
        if resource == "inferences":
            options, error, message = {"inferences": 20_000}, InferenceLimitError, "the 20000 inference limit was reached"
        else:
            options, error, message = {"timeout": 0.1}, TimeLimitError, r"the 0\.1 second time limit was reached"
        with under(tropical):
            previous = space.runtime.once("metta_evaluation_context(Context)")
            with pytest.raises(error, match=message):
                space.match(S.bad(S.x), under=name, **options).one()
            assert started == [2]
            assert finished == []
            assert current_algebra() == "tropical"
            assert space.runtime.once("metta_evaluation_context(Context)") == previous
        assert helper.eval(S["+"](1, 2)) == [3]
