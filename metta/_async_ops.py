"""Purpose: launch coroutine operations after their engine transaction commits.

Guarantees:
  - preparation creates no coroutine and performs no host work; ``start``
    schedules it on one process event loop only after the engine publishes the
    launch event [tested:
    test_a_transaction_commits_async_launch_before_its_landing;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - success, failure, and cancellation each land exactly once through
    ``metta_py_async_land/3`` and release the copied launch Context [tested:
    test_an_async_operation_answers_a_future_space,
    test_a_transaction_commits_async_launch_before_its_landing,
    test_cancelling_from_the_launch_observer_keeps_a_settled_future;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - delayed MeTTa injection sees the named space that launched the operation,
    and a landing observer sees terminal state before notification [tested:
    test_async_engine_injection_keeps_the_calling_named_space,
    test_a_landing_observer_can_await_the_future_it_observes;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - an accepted running cancellation remains cancelled even when the coroutine
    suppresses ``CancelledError``, and blocking landing observers do not stop
    unrelated coroutine tasks from landing [tested:
    test_accepted_async_cancellation_overrides_a_suppressed_cancel,
    test_a_landing_observer_can_await_another_async_future; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - a stopped loop drains or cancels every task, clears its published state,
    and a later launch starts a new loop; interpreter shutdown runs coroutine
    finalizers before closing the loop [tested:
    test_the_async_loop_recovers_from_stop_and_thread_start_failure,
    test_async_loop_shutdown_finalizes_pending_coroutines; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
Owns resources:
  - one daemon asyncio-loop thread from first launch until it stops or process
    exit, one transient attached-engine landing thread per completion, and one
    pending, cancelled-before-start, running, or cancelling record per async
    operation until landing or discard; the atexit handler drains and joins
    them [tested: test_async_loop_shutdown_finalizes_pending_coroutines,
    test_the_async_loop_recovers_from_stop_and_thread_start_failure,
    test_a_landing_observer_can_await_another_async_future; commit=39092863ae34184a9f955f185ff57c1ff177ec40].
Guarded by:
  - ``_LOCK`` protects pending/running/cancelling records, landing threads, and
    event-loop publication; asyncio owns each Task after it enters ``_RUNNING``.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import contextvars
import itertools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import _task_context
from ._engine import active_runtime, engine_thread
from .errors import NotReducible

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Pending:
    name: str
    args: tuple[Any, ...]
    context: int
    annotation: Any
    fn: Any
    call_space: Any


@dataclass
class _LoopState:
    loop: asyncio.AbstractEventLoop | None = None
    thread: threading.Thread | None = None
    starting: bool = False
    closing: bool = False
    shutting_down: bool = False
    ready: threading.Event = field(default_factory=threading.Event)
    error: BaseException | None = None


@dataclass(frozen=True)
class _Running:
    pending: _Pending
    task: asyncio.Task[Any]


_LOCK = threading.RLock()
_TOKENS = itertools.count(1)
_PENDING: dict[int, _Pending] = {}
_CANCELLED_PENDING: set[int] = set()
_STARTING: dict[int, _Pending] = {}
_RUNNING: dict[int, _Running] = {}
_CANCELLING: set[int] = set()
_LANDING_THREADS: set[threading.Thread] = set()
_LOOP_STATE = _LoopState()
_SHUTDOWN_TIMEOUT = 10.0


def prepare(name: str, tagged_args: list, parent_context: Any) -> int:
    """Retain one decoded call without invoking its coroutine function."""
    from . import _ops, _space  # noqa: PLC0415  -- callbacks import satellites lazily

    op = _ops.REGISTRY[name]
    args = tuple(_ops._decode_args(op, tagged_args))
    parent = parent_context if isinstance(parent_context, int) else None
    context = _task_context.fork(parent)
    token = next(_TOKENS)
    with _LOCK:
        _PENDING[token] = _Pending(
            name,
            args,
            context,
            op.return_annotation,
            op.fn,
            _space.current_space(),
        )
    return token


def start(token: int) -> bool:
    """Move one prepared call onto the shared coroutine event loop."""
    with _LOCK:
        pending = _PENDING.pop(token, None)
        cancelled = token in _CANCELLED_PENDING
        _CANCELLED_PENDING.discard(token)
        if pending is not None and not cancelled:
            _STARTING[token] = pending
    if pending is None:
        return False
    if cancelled:
        _queue_landing(token, pending, "cancelled", None)
        return True
    try:
        loop = _event_loop()
        context = _task_context.context_copy(pending.context)
        from . import _space  # noqa: PLC0415  -- bind the delayed call's captured engine space

        context.run(_space._ACTIVE_SPACE.set, pending.call_space)
    except BaseException as error:  # noqa: BLE001
        _fail_start(token, pending, error)
        return True

    def create_task() -> None:
        with _LOCK:
            if token not in _STARTING:
                return
        try:
            coroutine = pending.fn(*pending.args)
            task = loop.create_task(coroutine, context=context)
        except BaseException as error:  # noqa: BLE001
            _fail_start(token, pending, error)
            return
        with _LOCK:
            if _STARTING.pop(token, None) is None:
                task.cancel()
                return
            _RUNNING[token] = _Running(pending, task)
        task.add_done_callback(
            lambda completed: _completed(token, pending, completed),
            context=context,
        )

    try:
        loop.call_soon_threadsafe(create_task, context=context)
    except BaseException as error:  # noqa: BLE001
        _fail_start(token, pending, error)
    return True


def _fail_start(token: int, pending: _Pending, error: BaseException) -> None:
    """Land a startup failure only if cancellation did not settle it first."""
    with _LOCK:
        still_starting = _STARTING.pop(token, None) is not None
    if still_starting:
        _queue_landing(token, pending, "error", [type(error).__name__, error])


def discard(token: int) -> bool:
    """Release a call whose surrounding engine transaction rolled back."""
    with _LOCK:
        pending = _PENDING.pop(token, None)
        _CANCELLED_PENDING.discard(token)
    if pending is None:
        return False
    _task_context.release(pending.context)
    return True


def cancel(token: int) -> bool:
    """Request cancellation of a pending or running coroutine operation."""
    with _LOCK:
        pending = _PENDING.get(token)
        if pending is not None:
            _CANCELLED_PENDING.add(token)
            return True
        pending = _STARTING.pop(token, None)
        running = _RUNNING.get(token)
    if pending is not None:
        _queue_landing(token, pending, "cancelled", None)
        return True
    with _LOCK:
        if running is None or _RUNNING.get(token) is not running or running.task.done():
            return False
        # Task.cancel() is a request a coroutine may suppress. This marker is
        # the public operation's accepted terminal decision and therefore wins.
        # https://docs.python.org/3.14/library/asyncio-task.html#task-cancellation
        _CANCELLING.add(token)
    try:
        running.task.get_loop().call_soon_threadsafe(running.task.cancel)
    except RuntimeError:
        with _LOCK:
            claimed = _RUNNING.pop(token, None) is running
            _CANCELLING.discard(token)
        if claimed:
            _queue_landing(token, running.pending, "cancelled", None)
    return True


def _completed(token: int, pending: _Pending, task: asyncio.Task[Any]) -> None:
    from . import _ops  # noqa: PLC0415  -- completion uses the registry codec

    with _LOCK:
        running = _RUNNING.get(token)
        if running is None or running.task is not task:
            return
        _RUNNING.pop(token)
        cancellation_accepted = token in _CANCELLING
        _CANCELLING.discard(token)
    if cancellation_accepted or task.cancelled():
        _queue_landing(token, pending, "cancelled", None)
        return
    try:
        value = task.result()
        wire = _ops._encode_result(value, pending.annotation)
    except NotReducible:
        _queue_landing(token, pending, "ok", _ops._DECLINED)
    except BaseException as error:  # noqa: BLE001
        _queue_landing(token, pending, "error", [type(error).__name__, error])
    else:
        _queue_landing(token, pending, "ok", wire)


def _queue_landing(token: int, pending: _Pending, status: str, payload: Any) -> None:
    """Publish one terminal outcome without blocking the coroutine event loop."""
    context = contextvars.copy_context()

    def publish() -> None:
        try:
            with engine_thread():
                context.run(_land, token, pending, status, payload)
        finally:
            with _LOCK:
                _LANDING_THREADS.discard(threading.current_thread())

    thread = threading.Thread(
        target=publish,
        name=f"metta-async-land-{token}",
        daemon=True,
    )
    with _LOCK:
        _LANDING_THREADS.add(thread)
    try:
        thread.start()
    except BaseException:
        with _LOCK:
            _LANDING_THREADS.discard(thread)
        logger.exception("async operation %s could not start its landing worker", pending.name)
        # Thread creation failure must not strand the FutureSpace. The caller's
        # thread is the only remaining publication path.
        context.run(_land, token, pending, status, payload)


def _land(token: int, pending: _Pending, status: str, payload: Any) -> None:
    try:
        _publish_landing(token, status, payload)
    except BaseException:
        logger.exception("async operation %s could not publish its landing", pending.name)
    finally:
        with _LOCK:
            _CANCELLING.discard(token)
        _task_context.release(pending.context)


def _publish_landing(token: int, status: str, payload: Any) -> None:
    """Publish through the already-booted runtime or fail for the log boundary."""
    engine = active_runtime()
    if engine is None:
        msg = "the engine disappeared before an async operation landed"
        raise RuntimeError(msg)
    engine.do_must("metta_py_async_land", token, status, payload)


def _event_loop() -> asyncio.AbstractEventLoop:  # noqa: C901 -- startup, publication, teardown, and recovery share one locked state transition
    launch: threading.Thread | None = None
    with _LOCK:
        if _LOOP_STATE.shutting_down:
            msg = "the async operation event loop is shutting down"
            raise RuntimeError(msg)
        loop = _LOOP_STATE.loop
        thread = _LOOP_STATE.thread
        if (
            loop is not None
            and thread is not None
            and thread.is_alive()
            and not loop.is_closed()
            and not _LOOP_STATE.closing
        ):
            return loop
        if _LOOP_STATE.closing:
            msg = "the async operation event loop is closing"
            raise RuntimeError(msg)
        if loop is not None and (thread is None or not thread.is_alive() or loop.is_closed()):
            _LOOP_STATE.loop = None
            _LOOP_STATE.thread = None
        if not _LOOP_STATE.starting:
            _LOOP_STATE.starting = True
            _LOOP_STATE.closing = False
            _LOOP_STATE.error = None
            _LOOP_STATE.ready.clear()

            def serve() -> None:
                loop: asyncio.AbstractEventLoop | None = None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    with engine_thread():
                        with _LOCK:
                            _LOOP_STATE.loop = loop
                            _LOOP_STATE.starting = False
                        _LOOP_STATE.ready.set()
                        try:
                            loop.run_forever()
                        finally:
                            with _LOCK:
                                if _LOOP_STATE.loop is loop:
                                    _LOOP_STATE.closing = True
                            _drain_event_loop(loop)
                except BaseException as error:
                    logger.exception("the async operation event loop stopped")
                    with _LOCK:
                        _LOOP_STATE.error = error
                finally:
                    if loop is not None and not loop.is_closed():
                        loop.close()
                    asyncio.set_event_loop(None)
                    _land_orphaned_operations(
                        RuntimeError("the async operation event loop stopped before completion")
                    )
                    with _LOCK:
                        if _LOOP_STATE.loop is loop:
                            _LOOP_STATE.loop = None
                        if _LOOP_STATE.thread is threading.current_thread():
                            _LOOP_STATE.thread = None
                        _LOOP_STATE.starting = False
                        _LOOP_STATE.closing = False
                    _LOOP_STATE.ready.set()

            launch = threading.Thread(
                target=serve,
                name="metta-async-ops",
                daemon=True,
            )
            _LOOP_STATE.thread = launch
    if launch is not None:
        try:
            launch.start()
        except BaseException as error:
            with _LOCK:
                if _LOOP_STATE.thread is launch:
                    _LOOP_STATE.thread = None
                _LOOP_STATE.starting = False
                _LOOP_STATE.error = error
            _LOOP_STATE.ready.set()
            raise
    if not _LOOP_STATE.ready.wait(60):
        msg = "the async operation event loop did not start"
        raise RuntimeError(msg)
    with _LOCK:
        if _LOOP_STATE.error is not None:
            msg = "the async operation event loop failed during startup"
            raise RuntimeError(msg) from _LOOP_STATE.error
        if _LOOP_STATE.loop is None:
            msg = "the async operation event loop exited during startup"
            raise RuntimeError(msg)
        return _LOOP_STATE.loop


def _drain_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Finalize every asyncio resource before one loop thread exits."""
    with _LOCK:
        starting = list(_STARTING.items())
        _STARTING.clear()
    stopped = RuntimeError("the async operation event loop stopped before task creation")
    for token, pending in starting:
        _queue_landing(token, pending, "error", [type(stopped).__name__, stopped])

    # run_forever() returns after its current callback batch. Drain task done
    # callbacks, then async generators and the executor before loop.close().
    # https://docs.python.org/3.14/library/asyncio-eventloop.html#running-and-stopping-the-loop
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()
    if tasks:
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    # Completed tasks can still have done callbacks in the ready queue.
    loop.run_until_complete(asyncio.sleep(0))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.run_until_complete(loop.shutdown_default_executor())


def _land_orphaned_operations(error: BaseException) -> None:
    """Settle records left only when loop teardown itself failed."""
    with _LOCK:
        starting = list(_STARTING.items())
        running = list(_RUNNING.items())
        _STARTING.clear()
        _RUNNING.clear()
        for token, _ in running:
            _CANCELLING.discard(token)
    payload = [type(error).__name__, error]
    for token, pending in starting:
        _queue_landing(token, pending, "error", payload)
    for token, record in running:
        _queue_landing(token, record.pending, "error", payload)


def _shutdown_event_loop() -> None:
    """Stop and drain the process loop before daemon-thread teardown."""
    with _LOCK:
        _LOOP_STATE.shutting_down = True
        loop = _LOOP_STATE.loop
        thread = _LOOP_STATE.thread
        if loop is not None:
            _LOOP_STATE.closing = True
    if loop is not None and thread is not None and thread.is_alive():
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(loop.stop)
        if thread is not threading.current_thread():
            thread.join(_SHUTDOWN_TIMEOUT)
            if thread.is_alive():
                logger.error("the async operation event loop did not stop at exit")

    deadline = time.monotonic() + _SHUTDOWN_TIMEOUT
    while True:
        with _LOCK:
            landing = tuple(
                worker
                for worker in _LANDING_THREADS
                if worker is not threading.current_thread()
            )
        if not landing:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            logger.error("%d async landing worker(s) did not stop at exit", len(landing))
            return
        for worker in landing:
            worker.join(remaining)


atexit.register(_shutdown_event_loop)
