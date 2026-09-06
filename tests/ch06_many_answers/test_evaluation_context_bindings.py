"""Purpose: preserve binding preparation at carrier evaluation crossings.

Guarantees:
  - scoped symbol and atom bindings reach tagged guards and custom operations,
    including accounted execution and literal strings and host objects
    [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context_bindings.py -n 0;
    commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
"""

from __future__ import annotations

import pytest

from metta import Atom, Grounded, S, V, algebra


@pytest.mark.parametrize("atom_key", [False, True])
@pytest.mark.parametrize("inferences", [None, 1_000_000])
def test_tagged_guards_prepare_scoped_bindings(metta, atom_key, inferences):
    """A guard binding keeps its meaning when the guard carries an algebra."""
    with metta._new_space() as space:
        space.add(algebra.tagged_fact(2, S.binding_result(S.a)))
        key = S.threshold if atom_key else "threshold"
        with space.bind({key: 5}):
            answer = space.match(
                S.binding_result(V.x), under="ranked",
                where=S["=="](S.threshold, 5), inferences=inferences,
            )
            assert list(answer.x) == [S.a]


@pytest.mark.parametrize("atom_key", [False, True])
@pytest.mark.parametrize("inferences", [None, 1_000_000])
@pytest.mark.parametrize("payload", [5, "literal string", object()], ids=["number", "string", "object"])
def test_algebra_operations_prepare_scoped_bindings(
    metta, request, atom_key, inferences, payload
):
    """Binding values keep their literal type and host identity in a carrier."""
    space = metta._at(f"&{request.node.name}")
    seen = []

    def extend(_left: Atom, right: Atom) -> int:
        seen.append(right)
        return 7

    try:
        space.op(extend, name="context-bound-extend", effect="pureStructural")
        space.algebra(
            "context-bound-carrier", combine="+", extend="context-bound-extend",
            zero=0, one=1,
        )
        space.add(
            algebra.tagged_fact(S.weight, S.binding_base),
            algebra.tagged_rule(3, S.binding_derived, S.binding_base),
        )
        key = S.weight if atom_key else "weight"
        bound = Grounded(payload) if atom_key else payload
        with space.bind({key: bound}):
            answer = space.match(
                S.binding_derived, under="context-bound-carrier",
                inferences=inferences,
            ).one()
        assert answer.annotation == 7
        assert seen
        for value in seen:
            assert isinstance(value, Grounded)
            if type(payload) is object:
                assert value.value is payload
            else:
                assert value.value == payload
    finally:
        space.drop()
