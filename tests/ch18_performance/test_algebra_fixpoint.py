"""Purpose: a tagged program's engine fixpoint converges on cycles, scales, and is exact through formula.

Guarantees:
  - a cyclic program reaches the fixpoint the carrier's own arithmetic has:
    bool, set and tropical converge to the hand-computed values over a
    two-cycle graph, counting counts the derivations of an acyclic one, and
    the derived route still refuses the cycle by name when it is forced
    [tested: test_a_cyclic_program_converges_under_every_shipped_carrier,
    test_the_derived_route_still_refuses_a_cycle_when_forced; commit=55368cb4eeb641d2325194eff9d0925048814b76].
  - the formula carrier counts a shared fact once: two proofs through one
    fact reinterpret under prob to p_f (p_g + p_h - p_g p_h), where the sum
    over proofs answers p_f p_g + p_f p_h, and a cyclic program's formula
    reads back the exact probability [tested:
    test_the_formula_carrier_counts_each_proof_once,
    test_a_cyclic_program_is_exact_under_formula; commit=55368cb4eeb641d2325194eff9d0925048814b76].
  - the fixpoint route costs the engine's completion rather than Python rounds:
    a chain of n facts under the fixpoint spends fewer host-visible seconds
    than the derived route at n = 60, and the two routes agree on every
    answer [measured 2026-09-18: test_the_fixpoint_route_agrees_with_the_derived_route_and_costs_less;
    commit=55368cb4eeb641d2325194eff9d0925048814b76].
  - a custom algebra declares its negation, saturation and variable
    operations as claims the engine reads: a Python-declared carrier with a
    saturation test stops a sum over a cycle, and one with a negation counts
    a formula [tested: test_a_custom_algebra_declares_saturation_and_negation;
    commit=55368cb4eeb641d2325194eff9d0925048814b76].
  - a fixpoint answer keeps no derivation and says so: why() and under() on
    it refuse by name, except through formula [tested:
    test_a_fixpoint_answer_refuses_why_and_reinterprets_only_through_formula;
    commit=55368cb4eeb641d2325194eff9d0925048814b76].
  - a rule tagged (function F), or added with a callable tag, labels each
    instance with F over its premise tags on both routes, and such a label
    is not reinterpreted under another carrier [tested:
    test_a_rule_may_label_its_instances_by_a_function_of_its_premise_tags;
    commit=55368cb4eeb641d2325194eff9d0925048814b76].
"""

import time

import pytest

import metta as metta_root
import metta.algebra as algebra_module
from metta import S, V
from metta.algebra import AlgebraEvaluationError, evaluate


def _graph(space, edges, *, tag=1):
    for start, end, weight in edges:
        space.add_tagged_fact(weight, S.edge(S[start], S[end]))
    space.add_tagged_rule(tag, S.path(V.x, V.y), S.edge(V.x, V.y))
    space.add_tagged_rule(tag, S.path(V.x, V.z), S.edge(V.x, V.y), S.path(V.y, V.z))


CYCLE = (("a", "b", 0.6), ("b", "a", 0.5), ("a", "c", 0.2), ("b", "c", 0.3))


def test_a_cyclic_program_converges_under_every_shipped_carrier(metta):
    """A two-cycle reaches each carrier's own fixpoint, by hand: max, min, or."""
    with metta._new_space() as space:
        _graph(space, CYCLE)
        query = S.path(S.a, S.c)
        # bool and set take the strongest path: direct 0.2 beats 0.6 * 0.3.
        assert space.match(query, under=algebra_module.bool).one().annotation == pytest.approx(0.2)
        assert space.match(query, under=algebra_module.set).one().annotation == pytest.approx(0.2)
        # tropical sums costs: the rule's own tag 1 plus the edge, cheapest first.
        assert space.match(query, under=algebra_module.tropical).one().annotation == pytest.approx(1.2)
        # The route chose itself: a cyclic rule graph is the engine's fixpoint.
        answer = space.match(query, under=algebra_module.bool).one()
        assert any(decision.optimization == "tabled-fixpoint" and decision.applied for decision in answer.plan)
        # Every reachable pair, once each.
        reached = {tuple(row) for row in space.match(S.path(V.x, V.y), under=algebra_module.bool).rows}
        assert reached == {(S.a, S.a), (S.a, S.b), (S.a, S.c), (S.b, S.a), (S.b, S.b), (S.b, S.c)}


def test_the_derived_route_still_refuses_a_cycle_when_forced(metta):
    """derivations=True keeps the round-bounded evaluator and its refusal."""
    with metta._new_space() as space:
        _graph(space, CYCLE)
        with pytest.raises(AlgebraEvaluationError, match="did_not_reach_fixpoint"):
            evaluate(space, S.path(S.a, S.c), algebra="bool", derivations=True, max_rounds=3)


def test_counting_counts_derivations_on_the_fixpoint_route(metta):
    """Under counting every source reads as one, so the fixpoint is the number of proofs."""
    with metta._new_space() as space:
        _graph(space, (("a", "b", 0.6), ("b", "c", 0.5), ("a", "c", 0.2)))
        answers = evaluate(space, S.path(S.a, S.c), algebra="counting", derivations=False).answers
        assert [answer.annotation for answer in answers] == [2]


def test_the_formula_carrier_counts_each_proof_once(metta):
    """(f and g) or (f and h): the sum over proofs double counts f, the formula does not."""
    with metta._new_space() as space:
        p_f, p_g, p_h = 0.5, 0.6, 0.3
        space.add_tagged_fact(p_f, S.f())
        space.add_tagged_fact(p_g, S.g())
        space.add_tagged_fact(p_h, S.h())
        space.add_tagged_rule(1, S.goal(), S.f(), S.g())
        space.add_tagged_rule(1, S.goal(), S.f(), S.h())
        summed = space.match(S.goal(), under=algebra_module.prob).one().annotation
        assert summed == pytest.approx(p_f * p_g + p_f * p_h)
        exact = p_f * (p_g + p_h - p_g * p_h)
        # The derived route compiles its derivation tree to the diagram.
        derived = space.match(S.goal(), under=algebra_module.formula).one()
        assert derived.annotation.children[0] == S.formula
        assert derived.under(algebra_module.prob).annotation == pytest.approx(exact)
        # The fixpoint route builds the same diagram over the same variables.
        fixed = space.match(S.goal(), under=algebra_module.formula, derivations=False).one()
        assert fixed.under(algebra_module.prob).annotation == pytest.approx(exact)
        assert fixed.annotation == derived.annotation
        # The variables are the three facts, keyed by position, and the two
        # rule instances, keyed by the head they derived, each weighted as written.
        variables = algebra_module.formula_variables(space, fixed.annotation)
        facts = {key.children[2].value: weight.value for key, weight in variables if key.head == S.src}
        assert sorted(facts.values()) == sorted((p_f, p_g, p_h))
        assert [key.children[3] for key, _ in variables if key.head == S.rule] == [S.goal(), S.goal()]


def test_a_cyclic_program_is_exact_under_formula(metta):
    """P(path a c) over the two-cycle is 1 - (1 - 0.2)(1 - 0.6 * 0.3): the cycle adds nothing."""
    with metta._new_space() as space:
        _graph(space, CYCLE)
        answer = space.match(S.path(S.a, S.c), under=algebra_module.formula).one()
        assert answer.under(algebra_module.prob).annotation == pytest.approx(1 - (1 - 0.2) * (1 - 0.6 * 0.3))


def test_the_fixpoint_route_agrees_with_the_derived_route_and_costs_less(metta):
    """A chain of n facts: same answers, and the engine's completion beats Python rounds."""
    n = 60
    with metta._new_space() as space:
        _graph(space, tuple((f"n{i}", f"n{i + 1}", 1) for i in range(n)))
        query = S.path(S.n0, V.end)

        def timed(*, derivations):
            started = time.perf_counter()
            answers = evaluate(space, query, algebra="counting", derivations=derivations, max_rounds=n + 2).answers
            return time.perf_counter() - started, sorted((str(a.value), a.annotation) for a in answers)

        derived_seconds, derived = timed(derivations=True)
        fixpoint_seconds, fixed = timed(derivations=False)
        assert fixed == derived
        assert len(fixed) == n
        assert fixpoint_seconds < derived_seconds


def test_a_custom_algebra_declares_saturation_and_negation(metta):
    """A Python-declared carrier states its saturation and negation as claims the engine applies."""
    with metta._new_space() as space:
        near = algebra_module(
            "near-prob",
            plus=lambda a, b: a + b,
            times=lambda a, b: a * b,
            zero=0,
            one=1,
            negate=lambda a: 1 - a,
            saturated=lambda old, new: abs(old - new) < 1e-3,
        )
        assert near.negation == "near-prob-negate"
        assert near.saturation == "near-prob-saturated"
        claims = {
            str(row.claim): str(row.value)
            for row in metta_root.reflection[S.claim(S.semiring, S["near-prob"], V.claim, V.value)]
        }
        assert claims == {"negation": "near-prob-negate", "saturation": "near-prob-saturated"}
        # A sum over the two-cycle has no fixpoint; the declared saturation stops it.
        _graph(space, CYCLE)
        stopped = evaluate(space, S.path(S.a, S.c), algebra=near, derivations=False).answers
        assert len(stopped) == 1
        assert stopped[0].annotation > 0.2
        # The negation counts a formula exactly under the custom carrier.
        answer = space.match(S.path(S.a, S.c), under=algebra_module.formula).one()
        assert answer.under(near).annotation == pytest.approx(1 - (1 - 0.2) * (1 - 0.6 * 0.3))


def test_a_fixpoint_answer_refuses_why_and_reinterprets_only_through_formula(metta):
    """No proof tree is kept, and the refusal names the two remedies."""
    with metta._new_space() as space:
        _graph(space, CYCLE)
        answer = space.match(S.path(S.a, S.c), under=algebra_module.bool).one()
        with pytest.raises(AlgebraEvaluationError, match="keeps_no_derivation"):
            answer.why()
        with pytest.raises(AlgebraEvaluationError, match="keeps_no_derivation"):
            answer.under(algebra_module.prob)
        # A carrier without a negation cannot count a formula.
        compiled = space.match(S.path(S.a, S.c), under=algebra_module.formula).one()
        with pytest.raises(AlgebraEvaluationError, match="keeps_no_derivation"):
            compiled.under(algebra_module.tropical)


def test_derivations_needs_a_carrier(metta):
    """The route choice belongs to a tagged evaluation, so it needs under=."""
    with metta._new_space() as space, pytest.raises(TypeError, match="needs under="):
        space.match(S.anything(V.x), derivations=False)


def test_a_rule_may_label_its_instances_by_a_function_of_its_premise_tags(metta):
    """(function F) replaces the extend fold: NARS-shaped deduction takes the weaker premise."""
    with metta._new_space() as space:
        space.add_tagged_fact(0.6, S.p(S.a))
        space.add_tagged_fact(0.3, S.q(S.a))
        space.add_tagged_fact(0.9, S.p(S.b))
        space.add_tagged_fact(0.8, S.q(S.b))

        def weaker(left, right):
            return min(left, right)

        # A callable tag registers under its name and the rule stores (function rule-weaker).
        stored = space.add_tagged_rule(weaker, S.h(V.x), S.p(V.x), S.q(V.x))
        assert stored.children[1] == S.function(S["rule-weaker"])
        # A MeTTa equation of the same shape is the same spelling written by hand.
        space.add(S["="](S.stronger(V.a, V.b), S.max(V.a, V.b)))
        space.add_tagged_rule(S.function(S.stronger), S.k(V.x), S.p(V.x), S.q(V.x))

        by_hand = {S.a: 0.3, S.b: 0.8}
        for derivations in (True, False):
            answers = evaluate(space, S.h(V.x), algebra="prob", derivations=derivations).answers
            assert {answer.value.children[1]: answer.annotation for answer in answers} == pytest.approx(by_hand)
            answers = evaluate(space, S.k(V.x), algebra="prob", derivations=derivations).answers
            assert {answer.value.children[1]: answer.annotation for answer in answers} == pytest.approx({S.a: 0.6, S.b: 0.9})
        # The function computed in prob; another carrier cannot re-apply it.
        labelled = space.match(S.h(S.a), under=algebra_module.prob).one()
        with pytest.raises(AlgebraEvaluationError, match="not_reinterpretable"):
            labelled.under(algebra_module.tropical)
