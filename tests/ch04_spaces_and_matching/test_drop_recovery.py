"""Purpose: verify resource ownership across failed Space.drop calls.

Guarantees:
  - engine teardown failure preserves Python cleanup state for retry
    [tested: test_failed_engine_drop_keeps_subscriptions; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
"""

import pytest

from metta import MeTTa, S, V, foreign
from metta._errors.errors import MettaError


@pytest.mark.parametrize("stage", ["metta_py_clear_for_release", "metta_py_drop_space"])
def test_failed_engine_drop_keeps_subscriptions(metta, monkeypatch, stage):
    """A live observer remains registered until engine teardown succeeds."""
    space = metta._new_space()
    watch = space.subscribe(S.drop_recovery(V.x))
    original = type(space.runtime).must

    def fail(runtime, goal, **inputs):
        # Baseline anonymous release delegates to drop; intercept both names.
        release = stage == "metta_py_drop_space" and "metta_py_release_space" in goal
        if stage in goal or release:
            msg = "injected engine teardown failure"
            raise MettaError(msg)
        return original(runtime, goal, **inputs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(type(space.runtime), "must", fail)
            with pytest.raises(MettaError, match="injected engine teardown failure"):
                space.drop()
        space.add(S.drop_recovery(1))
        assert [event.atom for event in watch.drain()] == [S.drop_recovery(1)], (
            "failed engine teardown must not discard the space's subscriptions"
        )
        assert not space.dropped
        space.drop()
        assert space.dropped
    finally:
        watch.cancel()
        space.drop()


def test_failed_provider_unregistration_keeps_owned_backing_open(tmp_path, monkeypatch):
    """A journal is still owned while engine unregistration can be retried."""
    with MeTTa() as context:
        space = context.space(journal=tmp_path / "drop.jnl", schema={"edge": 2})
        backing = space._backing  # The file-owning provider has no public close observer.
        closed = []
        original_close = type(backing).close
        original_must = type(space.runtime).must

        def close(provider):
            closed.append(provider)
            return original_close(provider)

        def fail(runtime, goal, **inputs):
            if "metta_py_unregister_foreign" in goal:
                msg = "injected provider unregistration failure"
                raise MettaError(msg)
            return original_must(runtime, goal, **inputs)

        with monkeypatch.context() as patch:
            patch.setattr(type(backing), "close", close)
            with patch.context() as refusing:
                refusing.setattr(type(space.runtime), "must", fail)
                with pytest.raises(MettaError, match="injected provider unregistration failure"):
                    space.drop()
            assert closed == [], "failed unregistration must not close the registered backing"
            assert foreign.has_provider(space.name)
            space.add(S.edge(S.a, S.b))
            space.drop()
            assert closed == [backing], "successful drop must close the owned backing once"


def test_backing_close_failure_keeps_the_name_and_cleanup_retryable(tmp_path, monkeypatch):
    """Retry file cleanup without dropping a reused engine name or clearing a journal."""
    path = tmp_path / "retained.jnl"
    with MeTTa() as context:
        space = context.space(journal=path, schema={"edge": 2})
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
                space.drop()
            with pytest.raises(MettaError, match=r"call drop\(\) again"):
                space.add(S.edge(S.c, S.d))
            with context.space() as other:
                assert other.name != name, "unfinished cleanup must retain its anonymous name"
                space.drop()
                assert engine_drops == [name], "cleanup retry must not repeat engine teardown"
            assert close_calls == [backing, backing], "failed backing close must remain retryable"
        assert space.dropped
        with context.space(journal=path, schema={"edge": 2}) as reopened:
            assert reopened.atoms() == [S.edge(S.a, S.b)], "drop must preserve external journal data"
