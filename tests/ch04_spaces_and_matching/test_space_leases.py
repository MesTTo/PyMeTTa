"""Purpose: every Python handle of one space name shares one life, decided by the engine.

Guarantees: a retirement by any party marks every retained handle dead, a reused name
never answers an old handle, a handle born in an aborted transaction is dead, and lease
rows follow outstanding handles rather than historical names
[tested: test_a_native_drop_marks_every_retained_handle_dead,
test_aliases_share_one_life_and_a_reused_name_starts_another,
test_a_handle_born_in_an_aborted_transaction_is_dead,
test_lease_rows_follow_outstanding_handles; commit=a9b0ddb6db7f4837e1910b3e796ebee15a9bd81d].
"""

import gc

import pytest

from metta import MeTTa, S, Space, V
from metta._errors.errors import MettaError

ROW = S.lease_value


def _leases(runtime, name) -> int:
    return int(runtime.must(
        "atom_string(_Name, NameText), aggregate_all(count, metta_py_lease(_Name, _), N)", NameText=name,
    )["N"])


def _native_release(runtime, name) -> None:
    runtime.must("atom_string(_Name, NameText), metta_release_space(_Name)", NameText=name)


def test_a_native_drop_marks_every_retained_handle_dead():
    """A drop the handles never asked for still ends their life."""
    with MeTTa() as context:
        holder = context.space()
        holder.add(ROW(7))
        alias = Space(holder)
        name = holder.name
        assert _leases(context.runtime, name) == 1
        _native_release(context.runtime, name)
        assert holder.dropped and alias.dropped
        assert _leases(context.runtime, name) == 0
        for handle in (holder, alias):
            with pytest.raises(MettaError, match="is dead: its space was dropped"):
                handle.add(ROW(8))
        holder.drop()  # finishes this side's cleanup only; the engine is done
        assert holder.dropped


def test_aliases_share_one_life_and_a_reused_name_starts_another():
    """Two handles of one name die together; the name's next life is a stranger to them."""
    with MeTTa() as context:
        first = context.space("&lease-reuse")
        first.add(ROW(1))
        alias = Space(first)
        assert list(alias.eval(S.match(alias, ROW(V.x), V.x))) == [1]
        first.drop()
        assert first.dropped and alias.dropped
        with pytest.raises(MettaError, match="is dead"):
            alias.add(ROW(2))
        second = context.space("&lease-reuse")
        try:
            assert not second.dropped
            second.add(ROW(3))
            assert list(second.eval(S.match(second, ROW(V.x), V.x))) == [3]
            assert alias.dropped and first.dropped
            assert _leases(context.runtime, "&lease-reuse") == 1
        finally:
            second.drop()
        assert _leases(context.runtime, "&lease-reuse") == 0


def test_a_handle_born_in_an_aborted_transaction_is_dead():
    """The space never existed once the transaction rolled back, and its handle knows."""
    with MeTTa() as context:
        born = []

        def body():
            handle = context.space()
            handle.add(ROW(5))
            born.append(handle)
            assert not handle.dropped
            msg = "rollback-lease-birth"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="rollback-lease-birth"):
            context.self.transaction(body)
        (handle,) = born
        assert handle.dropped
        with pytest.raises(MettaError, match="did not commit"):
            handle.add(ROW(6))
        assert _leases(context.runtime, handle._name) == 0


def test_lease_rows_follow_outstanding_handles():
    """Transient handles leave no rows behind once collected and the engine is crossed."""
    with MeTTa() as context:
        for _ in range(64):
            Space("&lease-transient", _runtime=context.runtime)
        gc.collect()
        context.runtime.must("true")  # drains the deferred releases
        assert _leases(context.runtime, "&lease-transient") == 0
        kept = Space("&lease-transient", _runtime=context.runtime)
        for _ in range(64):
            Space("&lease-transient", _runtime=context.runtime)
        gc.collect()
        context.runtime.must("true")
        assert _leases(context.runtime, "&lease-transient") == 1, "the surviving handle keeps its lease"
        assert not kept.dropped
        kept.drop()
        assert _leases(context.runtime, "&lease-transient") == 0
