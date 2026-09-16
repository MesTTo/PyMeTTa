"""Purpose: a space dropped inside a transaction retires with the transaction's outcome.

Guarantees: an aborted transaction restores the space's rows, storage cache, scope
record and handle, and a committed one retires them only after the outcome
[tested: test_a_drop_inside_a_transaction_follows_its_outcome,
test_a_pending_drop_refuses_handle_operations_until_the_outcome,
test_cleanup_failure_after_a_committed_drop_is_retryable; commit=f9ef614a03bce1a1878d9b43fb7618df57ccfa21].
"""

from contextlib import nullcontext

import pytest

from metta import MeTTa, S, V
from metta._errors.errors import MettaError

ROW = S.retirement_value


def _storage(home, name):
    """Read the native storage view a name currently has, without recreating a dropped cache."""
    cached = bool(home.runtime.once(
        "atom_string(_Name, NameText), spaces:native_storage_module_cache(_Name, _)", NameText=name,
    ))
    rows = home.runtime.must(
        "atom_string(_Name, NameText), atom_string(_Relation, RelationText), "
        "findall(_Value, ( spaces:native_storage_module_cache(_Name, _Module), "
        "spaces:metta_storage_term(_Name, [_Relation, _Value], _, _Head), "
        "compound_name_arity(_Head, _Functor, _Arity), "
        "current_predicate(_Module:_Functor/_Arity), clause(_Module:_Head, true) ), Values)",
        NameText=name, RelationText=ROW.name,
    )["Values"]
    scope_dead = bool(home.runtime.once(
        "atom_string(_Name, NameText), lib_thread:scope_space_dead(_Name)", NameText=name,
    ))
    return {"cached": cached, "rows": rows, "scope_dead": scope_dead}


def _native_drop(home, name):
    home.runtime.must("atom_string(_Name, NameText), lib_thread:scope_drop_space(_Name)", NameText=name)


@pytest.mark.parametrize("abort", [False, True], ids=["commit", "abort"])
@pytest.mark.parametrize("action", ["python", "native"])
@pytest.mark.parametrize("scoped", [False, True], ids=["unscoped", "scoped"])
def test_a_drop_inside_a_transaction_follows_its_outcome(scoped, action, abort):
    """The V3 lifetime matrix: both doors, both scopes, both outcomes."""
    with MeTTa() as context:
        home = context.self
        home.run("(from (library lib_thread))")
        with home.scope() if scoped else nullcontext():
            holder = context.space()
            holder.add(ROW(7))
            name = holder.name
            assert _storage(home, name) == {"cached": True, "rows": [7], "scope_dead": False}
            assert not holder.dropped

            def body():
                if action == "python":
                    holder.drop()
                else:
                    _native_drop(home, name)
                assert not holder.dropped, "the durable state is decided by the outcome"
                if abort:
                    msg = "rollback-space-retirement"
                    raise RuntimeError(msg)

            if abort:
                with pytest.raises(RuntimeError, match="rollback-space-retirement"):
                    home.transaction(body)
                assert _storage(home, name) == {"cached": True, "rows": [7], "scope_dead": False}
                assert not holder.dropped
                assert list(holder.eval(S.match(S[name], ROW(V.value), V.value))) == [7]
            else:
                home.transaction(body)
                assert _storage(home, name) == {"cached": False, "rows": [], "scope_dead": scoped}
                assert holder.dropped


def test_a_pending_drop_refuses_handle_operations_until_the_outcome():
    """Between drop() and the outcome the handle is neither alive nor dead."""
    with MeTTa() as context:
        holder = context.space()
        holder.add(ROW(7))

        def body():
            holder.drop()
            with pytest.raises(MettaError, match="being dropped in the current transaction"):
                holder.add(ROW(8))
            holder.drop()  # a second drop while pending is the documented no-op
            msg = "rollback-space-retirement"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="rollback-space-retirement"):
            context.self.transaction(body)
        holder.add(ROW(8))
        assert sorted(holder.eval(S.match(holder, ROW(V.value), V.value))) == [7, 8]
        holder.drop()
        assert holder.dropped


def test_a_drop_outside_a_transaction_completes_before_returning():
    """Without a transaction the two phases run inside the one call."""
    with MeTTa() as context:
        holder = context.space()
        holder.add(ROW(7))
        name = holder.name
        holder.drop()
        assert holder.dropped
        assert _storage(context.self, name)["cached"] is False


def test_cleanup_failure_after_a_committed_drop_is_retryable(tmp_path, monkeypatch):
    """The commit is durable, the late cleanup error surfaces, and drop() finishes it."""
    with MeTTa() as context:
        space = context.space(journal=tmp_path / "retired.jnl", schema={"edge": 2})
        name = space.name
        space.add(S.edge(S.a, S.b))
        backing = space._backing  # Observe the owned file's release, not engine internals.
        close_calls = []
        engine_drops = []
        original_close = type(backing).close
        original_must = type(space.runtime).must

        def close(provider):
            close_calls.append(provider)
            if len(close_calls) == 1:
                msg = "injected backing close failure"
                raise OSError(msg)
            return original_close(provider)

        def record(runtime, goal, **inputs):
            if "metta_py_drop_space" in goal:
                engine_drops.append(inputs["Space"])
            return original_must(runtime, goal, **inputs)

        with monkeypatch.context() as patch:
            patch.setattr(type(backing), "close", close)
            patch.setattr(type(space.runtime), "must", record)
            with pytest.raises(OSError, match="injected backing close failure"):
                context.self.transaction(space.drop)
            assert not space.dropped
            with pytest.raises(MettaError, match=r"call drop\(\) again"):
                space.add(S.edge(S.c, S.d))
            space.drop()
            assert engine_drops == [name], "the retry must not repeat engine teardown"
            assert close_calls == [backing, backing]
        assert space.dropped
