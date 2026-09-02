"""Purpose: conformance tests for the suspended-engine scheduler and async ops.

Guarantees:
  - coroutine operations answer typed FutureSpace handles and settle success,
    failure, accepted cancellation, and independent repeated calls through the
    ordinary future lifecycle [tested:
    test_an_async_operation_answers_a_future_space,
    test_async_operation_failure_and_cancellation_settle_once,
    test_accepted_async_cancellation_overrides_a_suppressed_cancel,
    test_async_calls_are_effective_writes_with_independent_handles,
    test_a_failed_landing_watcher_does_not_rewrite_the_future,
    test_a_failed_landing_publication_settles_the_future_as_an_error,
    test_a_landing_observer_can_await_the_future_it_observes,
    test_a_landing_observer_can_await_another_async_future,
    test_cancelling_from_the_launch_observer_keeps_a_settled_future,
    test_async_engine_injection_keeps_the_calling_named_space,
    test_async_engine_injection_uses_the_registration_runtime,
    test_async_landing_uses_the_runtime_captured_during_prepare,
    test_a_landing_cancellation_is_not_swallowed;
    commit=WORKTREE]
  - an enclosing transaction publishes an async launch before starting the
    coroutine, then publishes landing independently; rollback discards the
    prepared call without starting it [tested:
    test_a_transaction_commits_async_launch_before_its_landing,
    test_a_direct_launch_watcher_failure_still_starts_and_lands,
    test_a_failed_launch_watcher_does_not_strand_committed_async_work,
    test_a_rolled_back_async_launch_never_starts_or_lands;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - oracleIO bodies detach onto transient workers while normal scheduled work
    keeps making progress, running cancellation remains truthful, and
    nondeterministic bodies hand off for every pull without losing answers [tested:
    test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work,
    test_an_oracle_generator_preserves_all_answers_across_dirty_handoffs;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - every public coordination or worker spawn door copies its launch Context,
    including scheduler engines, timer and race threads, EnginePool workers,
    AsyncMeTTa, coroutine tasks, and a nested spawn after child-local mutation [tested:
    test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
    test_context_release_linearizes_before_a_waiting_entry;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - FutureSpace iteration drains its terminal snapshot and separates that
    initial bag from later additions by publication position; async reflection
    names the public SpaceType and effective writesState contract, and loop
    teardown finalizes pending coroutines and permits recovery after unexpected
    stop or startup failure [tested:
    test_future_iteration_drains_the_terminal_snapshot,
    test_future_iteration_watermark_separates_snapshot_from_later_events,
    test_async_reflection_has_one_public_return_and_effect,
    test_the_async_loop_recovers_from_stop_and_thread_start_failure,
    test_async_loop_shutdown_finalizes_pending_coroutines; commit=1877bec75a9a22265c9222f0c0c538c8f65a983f]
"""

from __future__ import annotations

import asyncio
import contextvars
import os
import subprocess
import sys
import textwrap
import threading
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from metta import (
    Expression,
    Grounded,
    MeTTa,
    NotReducible,
    S,
    V,
    _task_context,
    aio,
    channel,
    every,
    par_map,
    race,
    spawn,
)
from metta._engine import runtime
from metta.errors import CompileError, EngineError, SubscriberError
from metta.parallel import EnginePool, FutureSpace


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _bounded_call(fn: Callable[[], Any], seconds: float = 10) -> Any:
    """Run a potentially blocking assertion behind an exact completion event."""
    done = threading.Event()
    values: list[Any] = []
    errors: list[BaseException] = []
    launch_context = contextvars.copy_context()

    def run() -> None:
        try:
            values.append(launch_context.run(fn))
        except BaseException as error:
            errors.append(error)
        finally:
            done.set()

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    assert done.wait(seconds), f"operation did not signal completion within {seconds}s"
    worker.join()
    if errors:
        raise errors[0]
    return values[0]


def _isolated_python(repo_root, source: str) -> subprocess.CompletedProcess[str]:
    """Run a singleton-lifecycle probe in a fresh interpreter."""
    environment = os.environ | {
        "METTA_PATH": str(repo_root),
        "PYTHONPATH": str(repo_root / "extensions" / "python"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _record_async_lifecycle(metta, name: str) -> tuple[list[Any], Any]:
    """Subscribe to both phases and return the owned cancellation handle."""
    seen: list[Any] = []
    subscription = metta._at("&metta").subscribe(
        S["async-op"](S[name], V.space, V.phase),
        seen.append,
    )
    return seen, subscription


def test_an_async_operation_answers_a_future_space(metta):
    """The decorator returns immediately; its payload lands in that space."""
    name = _unique("async-success")

    @metta.op(name=name, effect="pureStructural")
    async def increment(value: int) -> int:
        return value + 1

    try:
        future = metta.eval(S[name](41))[0]
        assert isinstance(future, FutureSpace)
        assert metta.type(S[name](41)) == S.SpaceType
        assert _bounded_call(lambda: list(future.wait())) == [42]

        raw_name = _unique("async-raw")
        with pytest.raises(TypeError, match="future-space"):
            metta.op(
                increment,
                name=raw_name,
                transport="raw",
                effect="pureStructural",
            )
    finally:
        metta.unregister_op(name)


def test_async_reflection_has_one_public_return_and_effect(metta):
    """Reflection describes the FutureSpace call, not the eventual Python value."""
    from metta.ops import registered
    from metta.vocabularies import EffectClass

    name = _unique("async-reflection")

    async def stringify(value: int) -> str:
        return str(value)

    metta.op(stringify, name=name, effect="pureStructural")
    try:
        claims = {
            str(atom)
            for atom in metta.atoms()
            if isinstance(atom, Expression) and S[name] in atom.children
        }
        assert f"(: {name} (-> Number SpaceType))" in claims
        assert f"(annotation {name} (return SpaceType))" in claims
        assert f"(annotation {name} (return String))" not in claims
        effects = metta._at("&metta").match(
            S.effect(S[name], V.effect)
        )
        assert [row.effect for row in effects] == [S.writesState]
        assert registered()[name].effect is EffectClass.writesState
    finally:
        metta.unregister_op(name)


def test_async_calls_are_effective_writes_with_independent_handles(metta):
    """Repeated pure-body calls allocate distinct cancellation domains."""
    name = _unique("async-independent")
    release = threading.Event()
    both_entered = threading.Event()
    calls = 0
    calls_lock = threading.Lock()

    async def answer() -> int:
        nonlocal calls
        with calls_lock:
            calls += 1
            if calls == 2:
                both_entered.set()
        await asyncio.to_thread(release.wait)
        return 7

    metta.op(answer, name=name, effect="pureStructural")
    try:
        first = metta.eval(S[name]())[0]
        second = metta.eval(S[name]())[0]
        assert first.name != second.name
        assert both_entered.wait(10)
        assert first.cancel() is True
        release.set()
        assert _bounded_call(lambda: list(first.wait())) == []
        assert _bounded_call(lambda: list(second.wait())) == [7]
        assert calls == 2
    finally:
        release.set()
        metta.unregister_op(name)


def test_future_iteration_drains_the_terminal_snapshot(metta, monkeypatch):
    """Settlement between a live snapshot and its check cannot hide the answer."""
    name = _unique("future-terminal-drain")
    entered = threading.Event()
    release = threading.Event()
    snapshot_taken = threading.Event()
    return_snapshot = threading.Event()
    iteration_done = threading.Event()
    iterated: list[Any] = []
    iteration_errors: list[BaseException] = []

    async def answer() -> int:
        entered.set()
        await asyncio.to_thread(release.wait)
        return 42

    metta.op(answer, name=name, effect="oracleIO")
    future = metta.eval(S[name]())[0]
    assert entered.wait(10)
    future.add(42)
    original_snapshot = FutureSpace._iteration_snapshot

    def gated_snapshot(self):
        snapshot = original_snapshot(self)
        if self is future:
            snapshot_taken.set()
            assert return_snapshot.wait(10)
        return snapshot

    monkeypatch.setattr(FutureSpace, "_iteration_snapshot", gated_snapshot)

    def iterate() -> None:
        try:
            iterated.extend(future)
        except BaseException as error:
            iteration_errors.append(error)
        finally:
            iteration_done.set()

    worker = threading.Thread(target=iterate, daemon=True)
    worker.start()
    try:
        assert snapshot_taken.wait(10)
        release.set()
        assert _bounded_call(lambda: list(future.wait())) == [42, 42]
        return_snapshot.set()
        assert iteration_done.wait(10)
        worker.join()
        assert iteration_errors == []
        assert iterated == [42, 42]
    finally:
        release.set()
        return_snapshot.set()
        metta.unregister_op(name)


def test_future_iteration_watermark_separates_snapshot_from_later_events(metta, monkeypatch):
    """An answer queued before the snapshot is present exactly once."""
    name = _unique("future-snapshot-watermark")
    entered = threading.Event()
    release = threading.Event()
    snapshot_entered = threading.Event()
    take_snapshot = threading.Event()
    iteration_done = threading.Event()
    iterated: list[Any] = []
    iteration_errors: list[BaseException] = []

    async def answer() -> int:
        entered.set()
        await asyncio.to_thread(release.wait)
        return 42

    metta.op(answer, name=name, effect="oracleIO")
    future = metta.eval(S[name]())[0]
    assert entered.wait(10)
    original_snapshot = FutureSpace._iteration_snapshot

    def gated_snapshot(self):
        if self is future:
            snapshot_entered.set()
            assert take_snapshot.wait(10)
        return original_snapshot(self)

    monkeypatch.setattr(FutureSpace, "_iteration_snapshot", gated_snapshot)

    def iterate() -> None:
        try:
            iterated.extend(future)
        except BaseException as error:
            iteration_errors.append(error)
        finally:
            iteration_done.set()

    worker = threading.Thread(target=iterate, daemon=True)
    worker.start()
    try:
        assert snapshot_entered.wait(10)
        release.set()
        assert _bounded_call(lambda: list(future.wait())) == [42]
        take_snapshot.set()
        assert iteration_done.wait(10)
        worker.join()
        assert iteration_errors == []
        assert iterated == [42]
    finally:
        release.set()
        take_snapshot.set()
        metta.unregister_op(name)


def test_async_operation_failure_and_cancellation_settle_once(metta):
    """Terminal coroutine states neither hang nor publish duplicate landings."""
    error_name = _unique("async-error")
    cancel_name = _unique("async-cancel")
    decline_name = _unique("async-decline")
    entered = threading.Event()
    release = threading.Event()

    async def fail() -> int:
        msg = "async host failure"
        raise ValueError(msg)

    async def block() -> int:
        entered.set()
        await asyncio.to_thread(release.wait, 20)
        return 99

    async def decline() -> int:
        raise NotReducible

    metta.op(fail, name=error_name, effect="pureStructural")
    metta.op(block, name=cancel_name, effect="oracleIO")
    metta.op(decline, name=decline_name, effect="pureStructural")
    reflection = metta._at("&metta")
    landed: list[Any] = []
    subscription = reflection.subscribe(
        S["async-op"](S[cancel_name], V.space, S.landing),
        landed.append,
    )
    try:
        failed = metta.eval(S[error_name]())[0]
        with pytest.raises(EngineError, match="async host failure"):
            _bounded_call(lambda: list(failed.wait()))

        declined = metta.eval(S[decline_name]())[0]
        assert _bounded_call(lambda: list(declined.wait())) == []

        cancelled = metta.eval(S[cancel_name]())[0]
        assert entered.wait(10)
        assert cancelled.cancel() is True
        assert _bounded_call(lambda: list(cancelled.wait())) == []
        assert cancelled.settled() is True
        assert len(landed) == 1
    finally:
        release.set()
        subscription.cancel()
        metta.unregister_op(error_name)
        metta.unregister_op(cancel_name)
        metta.unregister_op(decline_name)


def test_accepted_async_cancellation_overrides_a_suppressed_cancel(metta):
    """A true cancel answer is terminal even if the Task catches cancellation."""
    name = _unique("async-suppressed-cancel")
    entered = threading.Event()

    async def suppress_cancel() -> int:
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            return 42

    metta.op(suppress_cancel, name=name, effect="oracleIO")
    try:
        future = metta.eval(S[name]())[0]
        assert entered.wait(10)
        assert future.cancel() is True
        assert _bounded_call(lambda: list(future.wait())) == []
        assert future.settled() is True
    finally:
        metta.unregister_op(name)


def test_a_failed_landing_watcher_does_not_rewrite_the_future(metta):
    """A post-commit observer error is logged after the outcome is terminal."""
    name = _unique("async-landing-watcher")
    observed = threading.Event()

    async def answer() -> int:
        return 5

    def refuse_landing(_event) -> None:
        observed.set()
        msg = "landing watcher broke"
        raise ValueError(msg)

    metta.op(answer, name=name, effect="pureStructural")
    subscription = metta._at("&metta").subscribe(
        S["async-op"](S[name], V.space, S.landing),
        refuse_landing,
    )
    try:
        future = metta.eval(S[name]())[0]
        assert _bounded_call(lambda: list(future.wait())) == [5]
        assert observed.wait(10)
        assert future.settled() is True
    finally:
        subscription.cancel()
        metta.unregister_op(name)


def test_a_failed_landing_publication_settles_the_future_as_an_error(metta, monkeypatch):
    """A failed publication wakes the waiter with its terminal error."""
    from metta import _async_ops

    name = _unique("async-landing-publication")
    attempted = threading.Event()
    future = None

    async def answer() -> int:
        return 5

    def fail_publication(*_args) -> None:
        attempted.set()
        msg = "synthetic landing publication failure"
        raise RuntimeError(msg)

    metta.op(answer, name=name, effect="pureStructural")
    monkeypatch.setattr(_async_ops, "_publish_landing", fail_publication)
    try:
        future = metta.eval(S[name]())[0]
        assert attempted.wait(10)
        with pytest.raises(EngineError, match="synthetic landing publication failure"):
            _bounded_call(lambda: list(future.wait()), seconds=1)
        assert future.settled() is True
    finally:
        if future is not None:
            runtime().once(
                "(metta_future(Space, _, _Done) -> "
                "metta_future_complete(Space, _Done, cancelled) ; true)",
                Space=future.name,
            )
        metta.unregister_op(name)


def test_async_landing_uses_the_runtime_captured_during_prepare(metta, monkeypatch):
    """Completion does not reacquire a process-global runtime reference."""
    from metta import _async_ops

    name = _unique("async-captured-runtime")
    entered = threading.Event()
    release = threading.Event()

    async def answer() -> int:
        entered.set()
        await asyncio.to_thread(release.wait, 20)
        return 5

    metta.op(answer, name=name, effect="oracleIO")
    try:
        future = metta.eval(S[name]())[0]
        assert entered.wait(10)
        monkeypatch.setattr(_async_ops, "active_runtime", lambda: None)
        release.set()
        assert _bounded_call(lambda: list(future.wait())) == [5]
    finally:
        release.set()
        metta.unregister_op(name)


def test_a_landing_cancellation_is_not_swallowed(metta, monkeypatch):
    """Process-level cancellation leaves the landing function unchanged."""
    from metta import _async_ops

    context = _task_context.snapshot()
    pending = _async_ops._Pending(
        "cancelled-landing",
        (),
        context,
        Any,
        lambda: None,
        str(metta.name),
        metta.runtime,
    )

    def cancel_landing(*_args) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(_async_ops, "_publish_landing", cancel_landing)
    with pytest.raises(asyncio.CancelledError):
        _async_ops._land(-1, pending, "ok", None)


def test_a_landing_observer_can_await_the_future_it_observes(metta):
    """Landing means terminal, including inside the synchronous callback."""
    name = _unique("async-reentrant-landing")
    release = threading.Event()
    observed = threading.Event()
    answers: list[Any] = []

    async def answer() -> int:
        completed = await asyncio.to_thread(release.wait, 20)
        if not completed:
            msg = "reentrant landing gate was never released"
            raise RuntimeError(msg)
        return 13

    def await_landed(event) -> None:
        future = event.atom.children[2]
        answers.extend(future.wait())
        observed.set()

    metta.op(answer, name=name, effect="oracleIO")
    subscription = metta._at("&metta").subscribe(
        S["async-op"](S[name], V.space, S.landing),
        await_landed,
    )
    try:
        future = metta.eval(S[name]())[0]
        release.set()
        assert observed.wait(10)
        assert answers == [13]
        assert _bounded_call(lambda: list(future.wait())) == [13]
    finally:
        release.set()
        subscription.cancel()
        metta.unregister_op(name)


def test_a_landing_observer_can_await_another_async_future(metta):
    """One blocking landing observer cannot pin the coroutine event loop."""
    first_name = _unique("async-cross-observer")
    second_name = _unique("async-cross-observed")
    second_entered = threading.Event()
    release_second = threading.Event()
    observer_entered = threading.Event()
    observer_returned = threading.Event()
    observed_answers: list[Any] = []

    async def first() -> int:
        return 1

    async def second() -> int:
        second_entered.set()
        await asyncio.to_thread(release_second.wait)
        return 2

    metta.op(first, name=first_name, effect="writesState")
    metta.op(second, name=second_name, effect="oracleIO")
    second_future = metta.eval(S[second_name]())[0]
    assert second_entered.wait(10)

    def await_second(_event) -> None:
        observer_entered.set()
        observed_answers.extend(second_future.wait())
        observer_returned.set()

    subscription = metta._at("&metta").subscribe(
        S["async-op"](S[first_name], V.space, S.landing),
        await_second,
    )
    try:
        first_future = metta.eval(S[first_name]())[0]
        assert observer_entered.wait(10)
        release_second.set()
        assert observer_returned.wait(10)
        assert observed_answers == [2]
        assert _bounded_call(lambda: list(first_future.wait())) == [1]
        assert _bounded_call(lambda: list(second_future.wait())) == [2]
    finally:
        release_second.set()
        subscription.cancel()
        metta.unregister_op(first_name)
        metta.unregister_op(second_name)


def test_cancelling_from_the_launch_observer_keeps_a_settled_future(metta):
    """Pre-start cancellation lands after launch instead of discarding the handle."""
    name = _unique("async-cancel-on-launch")
    entered = threading.Event()
    cancelled: list[bool] = []
    landed = threading.Event()

    async def should_not_run() -> int:
        entered.set()
        return 1

    def cancel_launch(event) -> None:
        cancelled.append(event.atom.children[2].cancel())

    reflection = metta._at("&metta")
    metta.op(should_not_run, name=name, effect="writesState")
    cancelling = reflection.subscribe(
        S["async-op"](S[name], V.space, S.launch),
        cancel_launch,
    )
    observing = reflection.subscribe(
        S["async-op"](S[name], V.space, S.landing),
        lambda _event: landed.set(),
    )
    try:
        future = metta.eval(S[name]())[0]
        assert landed.wait(10)
        assert cancelled == [True]
        assert entered.is_set() is False
        assert _bounded_call(lambda: list(future.wait())) == []
        assert future.settled() is True
    finally:
        cancelling.cancel()
        observing.cancel()
        metta.unregister_op(name)


def test_async_engine_injection_keeps_the_calling_named_space(metta):
    """Delayed MeTTa injection captures the Prolog call context at launch."""
    name = _unique("async-injected-space")
    other = metta._new_space()

    async def where(engine: MeTTa) -> str:
        return str(engine.self.name)

    metta.op(where, name=name, effect="readOnlyLookup")
    try:
        future = other.eval(S[name]())[0]
        assert _bounded_call(lambda: list(future.wait())) == [Grounded(str(other.name))]
    finally:
        other.drop()
        metta.unregister_op(name)


def test_async_engine_injection_uses_the_registration_runtime(metta, monkeypatch):
    """Delayed injection never reacquires the process runtime accessor."""
    from metta import _space

    name = _unique("async-injected-runtime")

    async def where(engine: MeTTa) -> str:
        return str(engine.self.name)

    metta.op(where, name=name, effect="readOnlyLookup")

    def forbidden_runtime(*_args, **_kwargs):
        msg = "global runtime lookup reached from async task creation"
        raise RuntimeError(msg)

    monkeypatch.setattr(_space, "runtime", forbidden_runtime)
    try:
        future = metta.eval(S[name]())[0]
        assert _bounded_call(lambda: list(future.wait())) == [Grounded(str(metta.name))]
    finally:
        metta.unregister_op(name)


def test_a_transaction_commits_async_launch_before_its_landing(metta):
    """Commit releases launch; a gated coroutine lands in a later event."""
    name = _unique("async-transaction")
    entered = threading.Event()
    release = threading.Event()

    async def gated(value: int) -> int:
        entered.set()
        completed = await asyncio.to_thread(release.wait, 20)
        if not completed:
            msg = "transaction async gate was never released"
            raise RuntimeError(msg)
        return value + 1

    metta.op(gated, name=name, effect="oracleIO")
    seen, subscription = _record_async_lifecycle(metta, name)
    held: list[FutureSpace] = []
    try:

        def launch() -> None:
            held.extend(metta.eval(S[name](8)))
            assert not entered.is_set()
            assert seen == []

        metta.transaction(launch)
        future = held[0]
        assert entered.wait(10)
        assert [event.atom.children[-1] for event in seen] == [S.launch]
        assert future.settled() is False

        release.set()
        assert _bounded_call(lambda: list(future.wait())) == [9]
        assert [event.atom.children[-1] for event in seen] == [
            S.launch,
            S.landing,
        ]
    finally:
        release.set()
        subscription.cancel()
        metta.unregister_op(name)


def test_a_failed_launch_watcher_does_not_strand_committed_async_work(metta):
    """Post-commit observer failure does not skip the deferred coroutine start."""
    name = _unique("async-launch-watcher")

    async def answer() -> int:
        return 7

    def refuse_launch(_event) -> None:
        msg = "launch watcher broke"
        raise ValueError(msg)

    metta.op(answer, name=name, effect="pureStructural")
    subscription = metta._at("&metta").subscribe(
        S["async-op"](S[name], V.space, S.launch),
        refuse_launch,
    )
    held: list[FutureSpace] = []
    try:
        with pytest.raises(SubscriberError, match="launch watcher broke"):
            metta.transaction(lambda: held.extend(metta.eval(S[name]())))
        assert len(held) == 1
        assert _bounded_call(lambda: list(held[0].wait())) == [7]
    finally:
        subscription.cancel()
        metta.unregister_op(name)


def test_a_direct_launch_watcher_failure_still_starts_and_lands(metta):
    """The implicit launch segment also runs its post-commit start callback."""
    name = _unique("async-direct-launch-watcher")
    landed = threading.Event()

    async def answer() -> int:
        return 11

    def refuse_launch(_event) -> None:
        msg = "direct launch watcher broke"
        raise ValueError(msg)

    metta.op(answer, name=name, effect="pureStructural")
    reflection = metta._at("&metta")
    refusing = reflection.subscribe(
        S["async-op"](S[name], V.space, S.launch),
        refuse_launch,
    )
    observing = reflection.subscribe(
        S["async-op"](S[name], V.space, S.landing),
        lambda _event: landed.set(),
    )
    try:
        with pytest.raises(SubscriberError, match="direct launch watcher broke"):
            metta.eval(S[name]())
        assert landed.wait(10)
    finally:
        refusing.cancel()
        observing.cancel()
        metta.unregister_op(name)


def test_a_rolled_back_async_launch_never_starts_or_lands(metta):
    """Rollback releases the prepared call and publishes no lifecycle event."""
    name = _unique("async-rollback")
    entered = threading.Event()

    async def should_not_run() -> int:
        entered.set()
        return 1

    metta.op(should_not_run, name=name, effect="writesState")
    seen, subscription = _record_async_lifecycle(metta, name)
    held: list[FutureSpace] = []
    try:

        def roll_back() -> None:
            held.extend(metta.eval(S[name]()))
            msg = "discard prepared async operation"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="discard prepared async operation"):
            metta.transaction(roll_back)
        assert len(held) == 1
        assert entered.is_set() is False
        assert seen == []
        registry = runtime().once(
            "(metta_future(Space, _, _) -> Present = true ; Present = false)",
            Space=held[0].name,
        )
        assert registry is not None
        assert registry["Present"] == "false"
    finally:
        subscription.cancel()
        metta.unregister_op(name)


def test_define_async_refusal_names_both_actionable_remedies(metta):
    """The compile error points to the shipped future and host-async doors."""

    async def equation(value):
        return value

    with pytest.raises(CompileError) as refusal:
        metta.define(equation, name=_unique("async-definition"))
    message = str(refusal.value)
    assert "@space.op(effect=...)" in message
    assert "FutureSpace" in message
    assert "aio.AsyncMeTTa.call" in message


def test_a_blocking_oracle_uses_the_dirty_lane_without_pinning_normal_work(metta):
    """Blocked offloads release all bounded carriers and cancel truthfully."""
    name = _unique("blocking-oracle")
    lock = threading.Lock()
    entered_count = 0
    all_entered = threading.Event()
    release = threading.Event()

    def blocking_oracle(value: int) -> int:
        nonlocal entered_count
        with lock:
            entered_count += 1
            if entered_count == blocker_count:
                all_entered.set()
        if not release.wait(20):
            msg = "dirty-lane blocker was never released"
            raise RuntimeError(msg)
        return value

    metta.op(blocking_oracle, name=name, effect="oracleIO")
    blockers: list[FutureSpace] = []
    try:
        with metta:
            warmup = spawn(S["+"](1, 1))
            assert _bounded_call(lambda: list(warmup.wait())) == [2]
            row = runtime().once("metta_scheduler_lane_size(normal, Size)")
            assert row is not None
            normal_carriers = int(row["Size"])
            blocker_count = normal_carriers + 2
            try:
                blockers = [spawn(S[name](index)) for index in range(blocker_count)]
                assert all_entered.wait(10)
                assert blockers[0].cancel() is False
                assert blockers[0].settled() is False

                normal = spawn(S["+"](20, 22))
                assert _bounded_call(lambda: list(normal.wait())) == [42]
            finally:
                release.set()
                for index, future in enumerate(blockers):

                    def await_future(future: FutureSpace = future) -> list[Any]:
                        return list(future.wait())

                    expected = [] if index == 0 else [index]
                    assert _bounded_call(await_future) == expected
    finally:
        release.set()
        metta.unregister_op(name)


def test_an_oracle_generator_preserves_all_answers_across_dirty_handoffs(metta):
    """Each generator pull re-enters dirty and each answer returns to normal."""
    name = _unique("dirty-generator")

    def two_answers(value: int):
        yield value
        yield value + 1

    metta.op(two_answers, name=name, effect="oracleIO")
    try:
        with metta:
            future = spawn(S[name](7))
            assert _bounded_call(lambda: list(future.wait())) == [7, 8]
    finally:
        metta.unregister_op(name)


def test_context_release_linearizes_before_a_waiting_entry(monkeypatch):
    """A caller that retained a stale entry cannot enter after release returns."""
    token = _task_context.snapshot()
    retained = threading.Event()
    proceed = threading.Event()
    finished = threading.Event()
    values: list[str] = []
    errors: list[BaseException] = []
    original = _task_context._retained_entry

    def gated_entry(candidate: int):
        entry = original(candidate)
        if candidate == token:
            retained.set()
            assert proceed.wait(10)
        return entry

    monkeypatch.setattr(_task_context, "_retained_entry", gated_entry)

    def enter() -> None:
        try:
            values.append(_task_context.run(token, lambda: "entered"))
        except BaseException as error:
            errors.append(error)
        finally:
            finished.set()

    worker = threading.Thread(target=enter, daemon=True)
    worker.start()
    try:
        assert retained.wait(10)
        assert _task_context.release(token) is True
        proceed.set()
        assert finished.wait(10)
        worker.join()
        assert values == []
        assert len(errors) == 1
        assert isinstance(errors[0], KeyError)
        assert errors[0].args == (token,)
        assert _task_context.release(token) is False
    finally:
        proceed.set()
        _task_context.release(token)


def test_context_snapshot_crosses_every_spawn_door_including_thread_workers(metta):
    """Each execution door and channel transfer retain their launch value."""
    read_name = _unique("context-read")
    async_name = _unique("context-async")
    marker = contextvars.ContextVar(_unique("context-marker"), default="missing")
    async_release = threading.Event()

    def set_context(value: str) -> bool:
        marker.set(value)
        return True

    def read_context(_value: int) -> str:
        return marker.get()

    async def read_context_async() -> str:
        completed = await asyncio.to_thread(async_release.wait, 20)
        if not completed:
            msg = "async context gate was never released"
            raise RuntimeError(msg)
        return marker.get()

    metta.op(read_context, name=read_name, effect="readOnlyLookup")
    set_name = _unique("context-set")
    metta.op(set_context, name=set_name, effect="writesState")
    metta.op(read_context_async, name=async_name, effect="oracleIO")
    timer = None
    mailbox = None
    gates = []
    try:
        with metta:
            spawn_gate = metta._new_space()
            gates.append(spawn_gate)
            marker.set("spawn-snapshot")
            spawned = spawn(
                S.let(
                    V.ignored,
                    S["peek-atom"](spawn_gate, S.context_ready()),
                    S[read_name](0),
                )
            )
            marker.set("spawn-mutated")
            spawn_gate.add(S.context_ready())
            assert _bounded_call(lambda: list(spawned.wait())) == [Grounded("spawn-snapshot")]

            marker.set("nested-parent")
            outer = spawn(
                S.let(
                    V.ignored,
                    S[set_name]("nested-child"),
                    S.spawn(S[read_name](0)),
                )
            )
            nested = _bounded_call(lambda: list(outer.wait()))[0]
            assert isinstance(nested, FutureSpace)
            assert _bounded_call(lambda: list(nested.wait())) == [Grounded("nested-child")]

            marker.set("race-context")
            assert _bounded_call(lambda: race(S[read_name](1), S[read_name](2))) == Grounded(
                "race-context"
            )

            marker.set("map-context")
            assert tuple(par_map(S[read_name], [1, 2])) == (
                Grounded("map-context"),
                Grounded("map-context"),
            )

            timer_gate = metta._new_space()
            gates.append(timer_gate)
            marker.set("timer-snapshot")
            timer = every(
                0.001,
                S.let(
                    V.ignored,
                    S["peek-atom"](timer_gate, S.context_ready()),
                    S[read_name](0),
                ),
            )
            marker.set("timer-mutated")
            timer_gate.add(S.context_ready())
            arrivals = iter(timer)
            assert _bounded_call(lambda: next(arrivals)) == Grounded("timer-snapshot")
            assert timer.cancel() is True
            arrivals.close()

            pool_release = threading.Event()
            with EnginePool(1) as workers:
                marker.set("engine-pool-snapshot")
                request = workers.submit(
                    lambda: (
                        pool_release.wait(10),
                        marker.get(),
                    )[1]
                )
                marker.set("engine-pool-mutated")
                pool_release.set()
                assert request.result(timeout=10) == "engine-pool-snapshot"

            async def through_async_metta() -> str:
                worker_release = threading.Event()
                async with aio.AsyncMeTTa(metta=metta) as worker:
                    marker.set("aio-snapshot")
                    request = asyncio.create_task(
                        worker.call(
                            lambda _space: (
                                worker_release.wait(10),
                                marker.get(),
                            )[1]
                        )
                    )
                    marker.set("aio-mutated")
                    worker_release.set()
                    return await request

            assert _bounded_call(lambda: asyncio.run(through_async_metta())) == ("aio-snapshot")

            marker.set("async-op-snapshot")
            async_future = metta.eval(S[async_name]())[0]
            marker.set("async-op-mutated")
            async_release.set()
            assert _bounded_call(lambda: list(async_future.wait())) == [
                Grounded("async-op-snapshot")
            ]

            mailbox = channel(max=1)
            marker.set("channel-transfer")
            assert mailbox.send(Grounded(marker.get())) is True
            marker.set("channel-mutated")
            assert mailbox.recv(deadline=1) == Grounded("channel-transfer")
    finally:
        async_release.set()
        if timer is not None:
            try:
                timer.cancel()
            except (EngineError, OSError):
                pass
        if mailbox is not None:
            mailbox.close()
        for gate in gates:
            gate.drop()
        metta.unregister_op(read_name)
        metta.unregister_op(set_name)
        metta.unregister_op(async_name)


def test_the_async_loop_recovers_from_stop_and_thread_start_failure(repo_root):
    """A dead loop and one failed Thread.start do not poison later launches."""
    result = _isolated_python(
        repo_root,
        """
        import asyncio
        import threading

        from metta import MeTTa, S
        from metta import _async_ops
        from metta.errors import EngineError

        m = MeTTa(metta_path=str(__import__("os").environ["METTA_PATH"])).self
        stop_entered = threading.Event()
        stop_release = asyncio.Event()

        async def stop_loop() -> int:
            loop = asyncio.get_running_loop()
            stop_entered.set()
            await stop_release.wait()
            loop.stop()
            return 1

        async def ordinary() -> int:
            return 2

        m.op(stop_loop, name="probe-stop-loop", effect="writesState")
        first = m.eval(S["probe-stop-loop"]())[0]
        assert stop_entered.wait(10)
        stopped_loop = _async_ops._LOOP_STATE.loop
        stopped_thread = _async_ops._LOOP_STATE.thread
        assert stopped_loop is not None and stopped_thread is not None
        stopped_loop.call_soon_threadsafe(stop_release.set)
        stopped_thread.join(10)
        assert not stopped_thread.is_alive()
        assert list(first.wait()) == [1]

        m.op(ordinary, name="probe-loop-recovery", effect="writesState")
        recovered = m.eval(S["probe-loop-recovery"]())[0]
        assert list(recovered.wait()) == [2]
        replacement_thread = _async_ops._LOOP_STATE.thread
        replacement_loop = _async_ops._LOOP_STATE.loop
        assert replacement_thread is not None and replacement_loop is not None
        assert replacement_thread is not stopped_thread
        replacement_loop.call_soon_threadsafe(replacement_loop.stop)
        replacement_thread.join(10)
        assert not replacement_thread.is_alive()

        original_start = threading.Thread.start
        failed_once = False

        def fail_loop_start_once(self):
            global failed_once
            if self.name == "metta-async-ops" and not failed_once:
                failed_once = True
                raise RuntimeError("synthetic Thread.start failure")
            return original_start(self)

        threading.Thread.start = fail_loop_start_once
        try:
            failed = m.eval(S["probe-loop-recovery"]())[0]
        finally:
            threading.Thread.start = original_start
        try:
            list(failed.wait())
        except EngineError as error:
            assert "synthetic Thread.start failure" in str(error)
        else:
            raise AssertionError("the synthetic startup failure did not land")
        assert failed_once

        final = m.eval(S["probe-loop-recovery"]())[0]
        assert list(final.wait()) == [2]
        print("loop_recovered")
        """,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "loop_recovered" in result.stdout


def test_async_loop_shutdown_finalizes_pending_coroutines(repo_root):
    """The atexit loop drain executes a pending coroutine's finally block."""
    result = _isolated_python(
        repo_root,
        """
        import asyncio
        import threading

        from metta import MeTTa, S

        m = MeTTa(metta_path=str(__import__("os").environ["METTA_PATH"])).self
        entered = threading.Event()

        async def pending() -> int:
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                print("coroutine_finalized", flush=True)

        m.op(pending, name="probe-shutdown-finalizer", effect="oracleIO")
        m.eval(S["probe-shutdown-finalizer"]())
        assert entered.wait(10)
        print("main_returning", flush=True)
        """,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-2:] == ["main_returning", "coroutine_finalized"]
