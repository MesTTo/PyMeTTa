"""Purpose: the class withdrawal producer prepares native rows and reconciles Python records as two phases.

`prepare_withdrawal` closes the dependency graph over the requested homes and
withdraws the retiring plans' rows while every home is still admitted, touching
no Python record; `reconcile_withdrawal` restores instrumentation and
registrations only for the homes the outcome actually retired, refreshes the
survivors once, and skips the plans it has already completed so a retry after a
failure finishes the rest.
"""

from contextlib import ExitStack
from dataclasses import dataclass

import pytest

from metta import MeTTa, S, Space
from metta._declare import classes
from metta._declare.classes import declaration
from metta._errors.errors import EngineError

ROWS = "spaces:metta_native_pair('&metta', ['@owned-record', Home, _, _, _], _, _)"


def _catalog_rows(runtime, home: str) -> int:
    return int(runtime.must(
        f"aggregate_all(count, {ROWS}, N)", Home=home,
    )["N"])


def test_preparation_withdraws_rows_and_leaves_every_python_record_in_place():
    """Rows go in preparation; instrumentation, registrations and the declaration registry stay until reconciliation."""
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&WithdrawalPrepFirst", _runtime=m._rt)
        cleanup.callback(first.drop)

        @dataclass
        class WithdrawalPrepared:
            value: int

        first.define(WithdrawalPrepared)
        plan = declaration(WithdrawalPrepared)
        assert plan is not None
        home = str(plan.space.name)
        assert _catalog_rows(m._rt, home) >= 1
        receipt = classes.prepare_withdrawal((str(first.name),))
        assert receipt.homes == (home,)
        assert receipt.plans == (plan,)
        assert _catalog_rows(m._rt, home) == 0, "preparation withdraws the plan's rows"
        assert declaration(WithdrawalPrepared) is plan, "preparation leaves the declaration registry alone"
        assert isinstance(WithdrawalPrepared.__dict__.get("__metta__"), object)
        assert not plan.space.dropped, "preparation drops nothing"
        assert receipt.completed == set()
        # An abort supplies the empty set: nothing on the Python side moves.
        classes.reconcile_withdrawal(receipt, frozenset())
        assert declaration(WithdrawalPrepared) is plan
        # The outcome retired the home: instrumentation and registration go.
        classes.reconcile_withdrawal(receipt, frozenset({home}))
        assert declaration(WithdrawalPrepared) is None
        assert receipt.completed == {plan}
        plan.space.drop()


def test_a_failed_reconciliation_retries_only_the_work_not_done(monkeypatch):
    """The receipt records each completed plan, so a retry after a failure restores the rest exactly once."""
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&WithdrawalRetryFirst", _runtime=m._rt)
        cleanup.callback(first.drop)

        @dataclass
        class WithdrawalRetryLeft:
            peer: WithdrawalRetryRight  # noqa: F821 -- Python's deferred class annotations resolve the later sibling

        @dataclass
        class WithdrawalRetryRight:
            peer: WithdrawalRetryLeft

        first.define(WithdrawalRetryLeft)
        first.define(WithdrawalRetryRight)
        left, right = declaration(WithdrawalRetryLeft), declaration(WithdrawalRetryRight)
        receipt = classes.prepare_withdrawal((str(first.name),))
        assert set(receipt.plans) == {left, right}
        retired = frozenset({str(left.space.name), str(right.space.name)})
        failing = receipt.plans[1]
        original = type(failing).release_operations
        calls = []

        def fail_once(plan):
            if plan is failing and not calls:
                calls.append(plan)
                msg = "reconciliation failed once"
                raise OSError(msg)
            return original(plan)

        monkeypatch.setattr(type(failing), "release_operations", fail_once)
        with pytest.raises(OSError, match="reconciliation failed once"):
            classes.reconcile_withdrawal(receipt, retired)
        assert receipt.completed == {receipt.plans[0]}
        assert declaration(receipt.plans[0].cls) is None
        assert declaration(failing.cls) is failing
        classes.reconcile_withdrawal(receipt, retired)
        assert receipt.completed == set(receipt.plans)
        assert declaration(WithdrawalRetryLeft) is None and declaration(WithdrawalRetryRight) is None
        for plan in receipt.plans:
            plan.space.drop()


def test_a_live_borrower_keeps_its_class_out_of_the_withdrawal():
    """A class another live space still borrows survives the requesting home's withdrawal."""
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&WithdrawalBorrowFirst", _runtime=m._rt)
        second = Space("&WithdrawalBorrowSecond", _runtime=m._rt)
        cleanup.callback(first.drop)
        cleanup.callback(second.drop)

        @dataclass
        class WithdrawalShared:
            value: int

        first.define(WithdrawalShared)
        second.define(WithdrawalShared)
        plan = declaration(WithdrawalShared)
        receipt = classes.prepare_withdrawal((str(first.name),))
        assert receipt.plans == () and receipt.homes == ()
        assert plan in receipt.survivors
        classes.reconcile_withdrawal(receipt, frozenset({str(first.name)}))
        assert declaration(WithdrawalShared) is plan
        assert str(first.name) not in plan.borrowers


def _class_rows(runtime, home: str) -> int:
    return _catalog_rows(runtime, home)


def test_a_python_drop_retires_the_classes_it_takes_along_in_one_outcome():
    """Dropping a declaring space outside a transaction retires its class homes with it."""
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalDropFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalDropped:
            value: int

        first.define(WithdrawalDropped)
        plan = declaration(WithdrawalDropped)
        home = str(plan.space.name)
        first.drop()
        assert first.dropped and plan.space.dropped
        assert declaration(WithdrawalDropped) is None
        assert _class_rows(m._rt, home) == 0
        assert home not in m.space_names()


def test_a_rolled_back_drop_keeps_its_classes_and_their_rows():
    """An abort restores the declaring space, the class homes and the catalog rows together."""
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalRollbackFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalKept:
            value: int

        first.define(WithdrawalKept)
        plan = declaration(WithdrawalKept)
        home = str(plan.space.name)
        rows = _class_rows(m._rt, home)
        assert rows >= 1

        def body():
            first.drop()
            msg = "rollback-class-withdrawal"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="rollback-class-withdrawal"):
            m.transaction(body)
        assert not first.dropped and not plan.space.dropped
        assert declaration(WithdrawalKept) is plan
        assert _class_rows(m._rt, home) == rows
        assert WithdrawalKept(3).value == 3
        first.drop()
        assert declaration(WithdrawalKept) is None


def test_a_committed_drop_inside_a_transaction_reconciles_after_the_outcome():
    """Inside a transaction the class records stay until the outcome, then go with the homes."""
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalCommitFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalCommitted:
            value: int

        first.define(WithdrawalCommitted)
        plan = declaration(WithdrawalCommitted)
        seen = []

        def body():
            first.drop()
            seen.append(declaration(WithdrawalCommitted) is plan)

        m.transaction(body)
        assert seen == [True], "the Python records moved before the outcome"
        assert declaration(WithdrawalCommitted) is None
        assert first.dropped and plan.space.dropped


def test_a_drop_refused_at_commit_keeps_its_classes(overlap):
    """A write another engine committed into a class home refuses the drop's commit; the classes stay."""
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalRefusedFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalRefused:
            value: int

        first.define(WithdrawalRefused)
        plan = declaration(WithdrawalRefused)
        home = Space(str(plan.space.name), _runtime=m._rt)
        first_outcome, second_outcome = overlap(m, [lambda: home.add(S.written(1)), first.drop])
        assert first_outcome is None
        assert isinstance(second_outcome, EngineError)
        assert "retry the outer transaction" in str(second_outcome)
        assert not first.dropped and not plan.space.dropped
        assert declaration(WithdrawalRefused) is plan
        assert S.written(1) in home.atoms()
        first.drop()
        assert declaration(WithdrawalRefused) is None


def test_a_native_retirement_reconciles_the_class_records():
    """The engine retiring the declaring space on its own reaches the same reconciliation through the lease hook."""
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalNativeFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalNative:
            value: int

        first.define(WithdrawalNative)
        plan = declaration(WithdrawalNative)
        m._rt.must("atom_string(_Name, NameText), metta_release_space(_Name)", NameText=str(first.name))
        assert first.dropped
        assert declaration(WithdrawalNative) is None
        assert plan.space.dropped


def test_a_failed_reconciliation_is_retried_by_another_drop(monkeypatch):
    """A cleanup that fails after the outcome leaves the receipt pending; the lease hook or the next drop() finishes it.

    The engine's release hook fires after the host completion and reaches the
    same pending receipt, so the retry may already have run by the time the
    failed drop returns; either way the work completes exactly once.
    """
    with MeTTa() as context:
        m = context.self
        first = Space("&WithdrawalRetryDropFirst", _runtime=m._rt)

        @dataclass
        class WithdrawalRetried:
            value: int

        first.define(WithdrawalRetried)
        plan = declaration(WithdrawalRetried)
        original = type(plan).release_operations
        attempts = []

        def fail_once(target):
            if not attempts:
                attempts.append(target)
                msg = "reconciliation failed once"
                raise OSError(msg)
            return original(target)

        monkeypatch.setattr(type(plan), "release_operations", fail_once)
        with pytest.raises(OSError, match="reconciliation failed once"):
            first.drop()
        assert not first.dropped, "the handle still owes its cleanup"
        first.drop()
        assert first.dropped
        assert declaration(WithdrawalRetried) is None
        assert plan.space.dropped
        assert len(attempts) == 1, "the failed plan was released exactly once more"
