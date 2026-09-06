"""Purpose: keep carrier membership inside the ask's evaluation context.

Guarantees:
  - source annotations, operands and results see the selected algebra and demand
    [tested: test_carrier_predicates_share_the_operation_evaluation_context;
    commit=074dc0a88b1605c54824de677d586b6f60998bcf].
  - refusals and retained interpretation restore the complete enclosing context
    [tested: test_carrier_refusal_restores_the_enclosing_evaluation_context,
    test_retained_interpretation_uses_the_explicit_typed_carrier_context;
    commit=074dc0a88b1605c54824de677d586b6f60998bcf].
Owns resources:
  - fixtures drop their spaces and unregister their Python algebra operations.
"""

import pytest

import metta as m
from metta import S, V, algebra, ground, prov, tropical
from metta.algebra import AlgebraOperationError


def _engine_context(space):
    row = space.runtime.once("metta_evaluation_context(evaluation_context(A, L, D))")
    if not row:
        return None
    return row["A"], row["L"], row["D"]


@pytest.fixture
def typed_carrier_program(metta):
    """Observe one typed program after its declaration-time validation ends."""
    with metta._new_space() as space, space:
        observations = []
        state = {"record": False, "reject": None, "reject_after": 0}

        def observe(kind, *values):
            if state["record"]:
                observations.append((kind, values, m.current_algebra(), _engine_context(space)))

        def predicate(value):
            observe("predicate", value)
            visits = sum(kind == "predicate" and values == (value,) for kind, values, *_ in observations)
            return isinstance(value, int) and (
                value != state["reject"] or visits <= state["reject_after"]
            )

        def plus(left, right):
            observe("plus", left, right)
            return max(left, right)

        def times(left, right):
            observe("times", left, right)
            return left * right

        declared = algebra(
            "typed-carrier-context", plus=plus, times=times,
            zero=0, one=1, type=predicate, order="descending",
        )
        try:
            space.add(
                algebra.tagged_fact(2, S.carrier_context_seed),
                algebra.tagged_rule(3, S.carrier_context_result, S.carrier_context_seed),
            )
            state["record"] = True
            yield space, declared, state, observations
        finally:
            space.unregister_op("typed-carrier-context-plus")
            space.unregister_op("typed-carrier-context-times")


@pytest.mark.parametrize("inferences", [None, 1_000_000])
def test_carrier_predicates_share_the_operation_evaluation_context(typed_carrier_program, inferences):
    """Membership has the same carrier, limit and ordering as multiplication."""
    space, declared, _, observed = typed_carrier_program
    with m.under(tropical):
        previous = _engine_context(space)
        answer = space.match(
            S.carrier_context_result, under=declared, limit=2, inferences=inferences,
        ).one()
        assert answer.annotation == 6
        assert not answer.plan[0].applied
        assert m.current_algebra() == "tropical"
        assert _engine_context(space) == previous
    assert {kind for kind, *_ in observed} == {"predicate", "times"}
    assert all(
        active == declared.name and context == (declared.name, 2, "descending")
        for _, _, active, context in observed
    )
    values = {args[0] for kind, args, *_ in observed if kind == "predicate"}
    assert {2, 3, 6} <= values
    first_operation = next(index for index, row in enumerate(observed) if row[0] == "times")
    source_values = {row[1][0] for row in observed[:first_operation] if row[0] == "predicate"}
    assert {2, 3} <= source_values


@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("rejected,reject_after", [(2, 0), (3, 0), (2, 1), (6, 0)],
                         ids=["fact", "rule", "operand", "result"])
def test_carrier_refusal_restores_the_enclosing_evaluation_context(
    typed_carrier_program, inferences, rejected, reject_after,
):
    """Every validation phase restores scope before a subsequent evaluation."""
    space, declared, state, observed = typed_carrier_program
    state["reject"] = rejected
    state["reject_after"] = reject_after
    with m.under(tropical):
        previous = _engine_context(space)
        with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
            space.match(
                S.carrier_context_result, under=declared, limit=2, inferences=inferences,
            ).one()
        assert m.current_algebra() == "tropical"
        assert _engine_context(space) == previous
        assert any(kind == "predicate" and args == (rejected,) for kind, args, *_ in observed)
        assert all(
            active == declared.name and context == (declared.name, 2, "descending")
            for _, _, active, context in observed
        )
        state["reject"] = None
        assert space.match(S.carrier_context_result, under=declared).one().annotation == 6
        assert m.current_algebra() == "tropical"
        assert _engine_context(space) == previous


def test_retained_interpretation_uses_the_explicit_typed_carrier_context(metta):
    """A same-name source declaration cannot replace the retained object's type."""
    with metta._new_space() as owner, metta._new_space() as source:
        observed = []
        recording = False

        def observe(kind, *values):
            if recording:
                observed.append((kind, values, m.current_algebra(), _engine_context(source)))

        def predicate(value):
            observe("predicate", value)
            return isinstance(value, int)

        def times(left, right):
            observe("times", left, right)
            return left * right

        with owner:
            declared = algebra(
                "retained-typed-context", plus=max, times=times, zero=0, one=1,
                type=predicate, order="descending",
            )
        try:
            fact = algebra.tagged_fact(2, S.retained_carrier_seed)
            rule = algebra.tagged_rule(3, S.retained_carrier_result, S.retained_carrier_seed)
            source.add(fact, rule)
            answer = source.match(S.retained_carrier_result, under=prov).one()
            source.remove(fact, rule)
            source.algebra(
                declared.name, combine="+", extend="+", zero="", one="", type=str,
            )
            recording = True
            with source, m.under(tropical):
                previous = _engine_context(source)
                assert answer.under(declared).annotation == 6
                assert m.current_algebra() == "tropical"
                assert _engine_context(source) == previous
            assert {kind for kind, *_ in observed} == {"predicate", "times"}
            assert all(
                active == declared.name and context == (declared.name, 0, "descending")
                for _, _, active, context in observed
            )
        finally:
            owner.unregister_op("retained-typed-context-plus")
            owner.unregister_op("retained-typed-context-times")


@pytest.mark.parametrize("rejected", [None, 2, 6], ids=["accepted", "operand", "result"])
def test_direct_typed_operation_has_its_own_evaluation_context(typed_carrier_program, rejected):
    """Direct operations establish their declaration before checking operands."""
    space, declared, state, observed = typed_carrier_program
    state["reject"] = rejected
    with m.under(tropical):
        previous = _engine_context(space)
        if rejected is None:
            assert declared.extend_values(space, ground(2), ground(3)) == 6
        else:
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                declared.extend_values(space, ground(2), ground(3))
        assert m.current_algebra() == "tropical"
        assert _engine_context(space) == previous
    assert observed
    assert all(
        active == declared.name and context == (declared.name, 0, "descending")
        for _, _, active, context in observed
    )


@pytest.mark.parametrize("door", ["match", "stream", "answers"])
@pytest.mark.parametrize("rejected", [False, True], ids=["accepted", "refused"])
def test_captured_engine_annotations_keep_the_requested_context(typed_carrier_program, door, rejected):
    """Ordinary engine rows keep demand when their captured annotation is checked."""
    space, declared, state, observed = typed_carrier_program
    space.add(S.carrier_context_plain(S.a), S.carrier_context_plain(S.b))
    state["reject"] = 1 if rejected else None
    limit = 0 if door == "answers" else 2

    def consume():
        if door == "answers":
            return list(space.answers(
                f"(match {space.name} (carrier-context-plain $x) $x)", under=declared,
            ))
        if door == "stream":
            with space.stream(S.carrier_context_plain(V.x), under=declared, limit=2) as cursor:
                return list(cursor)
        return list(space.match(S.carrier_context_plain(V.x), under=declared, limit=2))

    with m.under(tropical):
        previous = _engine_context(space)
        if rejected:
            with pytest.raises(AlgebraOperationError, match="algebra_value_outside_carrier"):
                consume()
        else:
            answers = consume()
            assert len(answers) == 2
            assert all(answer.annotation == 1 for answer in answers)
        assert m.current_algebra() == "tropical"
        assert _engine_context(space) == previous
    assert observed
    assert all(
        active == declared.name and context == (declared.name, limit, "descending")
        for _, _, active, context in observed
    )
