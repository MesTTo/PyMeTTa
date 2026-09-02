"""Purpose: pin read-only inspection of a target's composite effect plan.

Guarantees:
  - Space.effect_plan follows nested compiled calls, returns every named
    operation with the lattice join, and executes none of them [tested:
    test_effect_plan_reports_nested_calls_without_executing_them;
    commit=d06621ddec911922c156c79ce68b2c35318e7fc1]
  - replacing an operation changes the next plan immediately, so Python does
    not retain a stale classification [tested:
    test_effect_plan_reads_replaced_operation_classification;
    commit=d06621ddec911922c156c79ce68b2c35318e7fc1]
"""

from __future__ import annotations

import uuid

from metta import S
from metta.ops import EffectPlan, registered
from metta.vocabularies import EffectClass


def _name(role: str) -> str:
    """Return a source-readable operation name unique to this test run."""
    return f"p42-plan-{role}-{uuid.uuid4().hex[:8]}"


def test_effect_plan_reports_nested_calls_without_executing_them(metta):
    """Inspect a compiled call chain and retain each contributing operation."""
    read_name = _name("read")
    write_name = _name("write")
    target_name = _name("target")
    called = []

    @metta.op(name=read_name, effect=EffectClass.readOnlyLookup)
    def read(value):
        called.append((read_name, value))
        return value

    @metta.op(name=write_name, effect=EffectClass.writesState)
    def write(value):
        called.append((write_name, value))
        return value

    try:
        metta.run(
            f"(= ({target_name} $x) "
            f"(let $seen ({read_name} $x) ({write_name} $seen)))"
        )
        for target in (S[target_name](7), f"({target_name} 7)"):
            plan = metta.effect_plan(target)
            assert isinstance(plan, EffectPlan)
            assert plan.operations == (
                ("let", EffectClass.pureStructural),
                (read_name, EffectClass.readOnlyLookup),
                (write_name, EffectClass.writesState),
            )
            assert plan.effect is EffectClass.writesState
            assert (
                EffectClass.compose(effect for _, effect in plan.operations)
                is plan.effect
            )
        assert called == []
    finally:
        for name in (read_name, write_name):
            if name in registered():
                metta.unregister_op(name)


def test_effect_plan_reads_replaced_operation_classification(metta):
    """Read the current catalog after an operation is removed and replaced."""
    operation_name = _name("replace")
    target_name = _name("replacement-target")
    called = []

    def implementation(value):
        called.append(value)
        return value

    metta.op(
        implementation,
        name=operation_name,
        effect=EffectClass.readOnlyLookup,
    )
    try:
        metta.run(f"(= ({target_name} $x) ({operation_name} $x))")
        before = metta.effect_plan(S[target_name](7))
        assert before.operations == (
            (operation_name, EffectClass.readOnlyLookup),
        )
        assert before.effect is EffectClass.readOnlyLookup

        metta.unregister_op(operation_name)
        metta.op(
            implementation,
            name=operation_name,
            effect=EffectClass.oracleIO,
        )
        after = metta.effect_plan(S[target_name](7))
        assert after.operations == ((operation_name, EffectClass.oracleIO),)
        assert after.effect is EffectClass.oracleIO
        assert called == []
    finally:
        if operation_name in registered():
            metta.unregister_op(operation_name)
