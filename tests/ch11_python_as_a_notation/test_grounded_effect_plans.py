"""Purpose: inspect live grounded callables through native effect plans.

Guarantees:
  - source and compiled plans include opaque callable effects without running
    them; data and quotation remain structural [tested:
    test_grounded_effect_plans_classify_calls_without_executing_them,
    test_grounded_effect_plans_keep_nonapplicable_and_quoted_values_structural;
    commit=84c73d0d703be50c3520b2e08488581e77a7ce3f]
"""

import pytest

from metta import Expression, Grounded, MeTTa, S, V
from metta.vocabularies import EffectClass


@pytest.mark.parametrize("reference", [False, True])
def test_grounded_effect_plans_classify_calls_without_executing_them(reference):
    """The native provider decides applicability even through a reference row."""
    with MeTTa() as context:
        m = context.self
        calls = []

        def operation(value):
            calls.append(value)
            return value + 1

        atom = Grounded(operation)
        with m._new_space() as home, m._new_space() as peer:
            home.add(S["="](S["opaque-effect-call"](V.value), Expression([atom, V.value])))
            if reference:
                peer.from_(home)
            target = peer if reference else home
            for source in (Expression([atom, 3]), S["opaque-effect-call"](3)):
                plan = target.effect_plan(source)
                assert plan.effect is EffectClass.oracleIO
                assert ("<dynamic-operation>", EffectClass.oracleIO) in plan.operations
                assert calls == []
            assert target.eval(S["opaque-effect-call"](3)) == [4]
            assert calls == [3]


@pytest.mark.parametrize("value", [object(), 1, 1.5, "inert"])
def test_grounded_effect_plans_keep_nonapplicable_and_quoted_values_structural(value):
    """An inert head or a quoted callable does not execute a host operation."""
    with MeTTa() as context:
        m = context.self
        plan = m.effect_plan(Expression([Grounded(value), 3]))
        assert plan.effect is EffectClass.pureStructural

        def forbidden():
            raise AssertionError

        quoted = S.noeval(Expression([Grounded(forbidden)]))
        assert m.effect_plan(quoted).effect is EffectClass.pureStructural
