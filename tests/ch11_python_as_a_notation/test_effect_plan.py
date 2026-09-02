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
  - AsyncMeTTa carries the same resolvable EffectPlan result type and performs
    the analysis on its worker without executing the target [tested:
    test_async_effect_plan_retains_the_sync_contract;
    commit=ce375389e773becefd3823878ba759a1f54face3]
"""

from __future__ import annotations

import asyncio
import uuid
from typing import get_type_hints

from metta import S, aio
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


def test_async_effect_plan_retains_the_sync_contract(metta):
    """Resolve its public type and inspect a target on the engine worker."""
    operation_name = _name("async-read")
    target_name = _name("async-target")
    called = []

    async def inspect():
        async with aio.AsyncMeTTa(metta=metta._new_space()) as async_metta:
            def implementation(value):
                called.append(value)
                return value

            await async_metta.op(
                implementation,
                name=operation_name,
                effect=EffectClass.readOnlyLookup,
            )
            try:
                await async_metta.run(
                    f"(= ({target_name} $x) ({operation_name} $x))"
                )
                return await async_metta.effect_plan(S[target_name](7))
            finally:
                await async_metta.unregister_op(operation_name)

    assert get_type_hints(aio.AsyncMeTTa.effect_plan)["return"] is EffectPlan
    plan = asyncio.run(inspect())
    assert plan.operations == ((operation_name, EffectClass.readOnlyLookup),)
    assert plan.effect is EffectClass.readOnlyLookup
    assert called == []
