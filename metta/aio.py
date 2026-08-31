"""Purpose: the same engine without blocking an event loop. AsyncMeTTa
proxies a MeTTa space onto one dedicated worker thread that holds an
attached Prolog engine, the aiosqlite architecture (one thread per
connection, a request queue, results delivered back through the loop), so
awaiting a long query lets every other coroutine keep running. One engine
per process stays the rule: calls are serialized, and the win is a live
event loop, never parallel evaluation. interrupt() stops the running
evaluation through the engine's own thread_signal, the sqlite3 reading,
and a cancelled task fires it on its own call, so asyncio timeouts stop
the engine instead of abandoning it.
Guarantees:
  - async solve, Linda verbs, watch, class/type dispatch, and the two
    transaction laws execute on the owning worker [tested:
    test_aio_structural_surface_behaves; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - interrupt_if_running throws the same reserved structured exception as
    shim resource guards [tested test_aio_interrupt_stops_the_running_evaluation]
  - close refuses new work, interrupts a running request, rejects queued
    requests, and bounds the worker join [tested test_aio_close_interrupts_work]
  - the transition drain discards only a structured interrupt and fails
    closed on every other error [tested
    test_aio_drain_only_discards_structured_interrupt]
  - a cancelled acquisition releases what the worker finished rather than
    leaving it live and unowned: the worker thread a cancelled connect
    launched, the registered subscription, the installed assumption facts
    [tested: test_aio_cancelled_connect_leaves_no_live_worker,
    test_aio_cancelled_subscription_registration_cancels_it,
    test_aio_cancelled_assuming_removes_the_facts_it_installed;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - aclose refuses further work only after the engine has let go, so a close
    that failed is retryable, and the stream's terminator reaches a consumer
    whose queue is full [tested:
    test_aio_a_failed_cursor_close_stays_retryable,
    test_aio_a_failed_subscription_close_stays_retryable,
    test_aio_the_close_sentinel_survives_a_full_queue; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - an event queue is published only once its registration succeeded, and its
    bound is refused unless it is a count of events [tested:
    test_aio_a_failed_subscription_publishes_no_queue,
    test_the_async_queue_bound_is_refused_the_same_way; commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - an abandoned live owner emits ResourceWarning and registered workers
    detach during interpreter shutdown [tested test_aio_leak_warns_and_stop_joins,
    test_aio_shutdown_handler_stops_forgotten_workers]
  - interpreter shutdown attempts every worker and reports all expected
    stop failures together [tested test_aio_shutdown_handler_attempts_every_worker]
  - interpreter shutdown without live workers does not initialize the
    optional engine bridge [tested test_aio_empty_shutdown_does_not_import_janus]
  - async names and save formats retain the synchronous surface's contextual
    types [tested: test_canonical_context_types_replace_public_newtypes;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async head-named declaration methods reuse the catalog-generated policy aliases and
    own no duplicate Literal lists [tested: tests/checks/check_policy_inventory.py;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - all fifteen synchronous declaration heads have asynchronous mirrors,
    including ``reacts`` for ``(on ...)`` while ``reaction`` remains, and no
    ``declare_*`` aliases [tested:
    test_aio_covers_the_whole_synchronous_surface,
    test_m7_narrow_core_surface; commit=0cfc68a483d8d64fb499e53bbe9a3cc63f68990f]
  - async cast preserves a concrete target class as its static return type and
    keeps the target positional-only [tested
    test_target_type_overloads_preserve_the_requested_class,
    test_cast_target_is_positional_only]
  - async space forwards anonymous-space inheritance, restriction, and grants
    on the owning worker [tested:
    test_async_space_forwards_restriction_and_grants; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async scoped limits forward stack byte bounds through the synchronous
    task-local scope [tested: test_stack_limit_is_carried_to_the_limited_six_seam;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - reader-token registration and removal run on the owning engine worker and
    mirror the synchronous surface [tested:
    test_aio_plain_methods_forward_on_the_worker and
    test_async_anonymous_space_repr_keeps_the_submitting_site;
    commit=50d1de4d0ead4a0c3997f9b2ef58631bbafaede3]
  - async eval mirrors the synchronous single answer shape without a
    residuals flag [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async function handles consume the synchronous Answers surface on their
    owning worker, including the composite ``neg`` operator word [tested:
    test_aio_structural_surface_behaves; commit=8ec44dec3cafba5981e7cf712749cca0e1bdcc45]
  - async operation registration requires and forwards the canonical effect
    argument [tested: test_aio_declare_and_register_delegations_land;
    commit=3cfbe0d7417b1c453c2dc12d47e2e47e7de461f7]
  - execution-policy scopes cross the worker hop and never change awaited
    return shapes [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - image reaches the synchronous declaration owner on the engine
    worker [tested: test_aio_covers_the_whole_synchronous_surface;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - async peek and take keep event-loop threads unblocked while the engine
    worker performs the synchronous Linda wait [tested:
    test_async_peek_and_take_mirror_the_space_handle; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - async match forwards the submitting task's scoped or explicit algebra,
    and sample mirrors the synchronous random.choices-shaped door [tested:
    test_aio_covers_the_whole_synchronous_surface; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - async reification, world evaluation, and commit keep every engine crossing
    on the owning worker while immutable atom snapshots remain directly
    readable [tested: test_async_worlds_stay_on_the_owning_worker;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - async coverage, compensation declarations, and saga recovery keep their
    complete synchronous scope on one owning worker [tested:
    test_async_saga_and_world_coverage_stay_on_the_owning_worker;
    commit=173eeed021beb360b5e5f9f8461889e27190affc]
Owns:
  - each owning AsyncMeTTa owns one daemon worker and its attached Prolog
    engine until aclose(), stop(), or the atexit handler releases it [tested
    test_aio_leak_warns_and_stop_joins]
Guarded by:
  - _state_lock publishes worker state and engine identity; _transition
    serializes request completion with interruption [tested
    test_aio_interrupt_stops_the_running_evaluation]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import asyncio
import atexit
import builtins as _builtins
import contextlib
import contextvars
import logging
import math
import os
import queue
import re as _re
import threading
import warnings
import weakref
from collections.abc import Callable, Coroutine, Iterable, Mapping, Sequence
from types import TracebackType
from typing import Any, Final, Literal, Self, TypeVar, overload

from ._api_types import _DEFAULT_SPACE, _SpaceId
from ._engine import Runtime, bridge, runtime
from ._name_mapping import OperatorRecipe, operator_attribute_target
from ._space import Space, _creation_site
from ._space_objects import require_deadline
from ._under import _UNSET
from ._under import selected as _selected_under
from .atoms import Atom, Expression, Symbol
from .errors import Interrupted, MettaError, Timeout
from .results import Rows
from .subscribe import SUBSCRIPTION_QUEUE_MAX, _capacity
from .vocabularies import (
    AgendaPolicy,
    AnswerPolicy,
    Atomicity,
    Delivery,
    Determinism,
    EffectClass,
    EventOrder,
    Fidelity,
    ImageMode,
    OnError,
    SaveFormat,
    SemiringOrder,
    SourceKind,
    World,
)

logger = logging.getLogger(__name__)

__all__ = ["AsyncMeTTa", "connect"]

DEFAULT_CLOSE_TIMEOUT: Final[float] = 10.0
_LIVE_WORKERS: weakref.WeakSet[_EngineThread] = weakref.WeakSet()
_LIVE_WORKERS_LOCK = threading.Lock()
_CastT = TypeVar("_CastT")


def _set_future_exception(future: asyncio.Future[None], failure: BaseException) -> None:
    if not future.done():
        future.set_exception(failure)


def _set_future_result(future: asyncio.Future[None]) -> None:
    if not future.done():
        future.set_result(None)


class _Request:
    __slots__ = ("abandoned", "context", "fn", "future", "loop", "target")

    def __init__(self, fn, target, loop, future) -> None:
        self.fn = fn
        self.target = target
        self.loop = loop
        self.future = future
        self.abandoned = threading.Event()
        # The submitting task's contextvars, so scoped state (limits(),
        # an open batch) crosses to the worker thread with the request,
        # which is what makes the with-blocks async-correct THROUGH the
        # thread hop and not only beside it.
        self.context = contextvars.copy_context()


class _EngineThread:
    """The one worker a connection owns and its spaces borrow: an attached
    Prolog engine, a request queue, and the interruption state.

    Interruption is raced against completion, so both sides go through one
    transition lock: the worker changes the current request under it, and
    a signaller reads the current request and sends thread_signal under
    it. A signal that lands after its goal finished is eaten by a drain
    call the worker makes inside the same critical section, so it can
    never poison the next request, the failure mode an unconditional
    thread_signal has on an idle thread.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self) -> None:
        self.work: queue.Queue[_Request | None] = queue.Queue()
        self.thread: threading.Thread | None = None
        self._transition = threading.Lock()
        self._state_lock = threading.Lock()
        self._state = "unstarted"
        self._failure: BaseException | None = None
        self._startup: asyncio.Future[None] | None = None
        self._current: _Request | None = None
        self._swi_thread: Any = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        started: asyncio.Future[None] | None = None
        launch = False
        with self._state_lock:
            if self._state == "live":
                if self.thread is not None and self.thread.is_alive():
                    return
                self._fail_locked(RuntimeError("the worker thread stopped"))
            if self._state == "starting":
                started = self._startup
                if started is None:
                    msg = "starting AsyncMeTTa has no startup future"
                    raise RuntimeError(msg)
                launch = False
            elif self._state in ("failed", "closing", "closed"):
                self._raise_state_locked()
            else:
                started = loop.create_future()
                self._startup = started
                self._state = "starting"
                launch = True

        if started is None:
            msg = "AsyncMeTTa startup did not create a future"
            raise RuntimeError(msg)
        if not launch:
            # Another caller launched this worker and owns stopping it. The
            # shield keeps THIS caller's cancellation off the shared startup
            # future, which would otherwise cancel the launcher's wait too.
            await asyncio.shield(started)
            return

        def worker() -> None:
            # A persistent attached engine makes this thread first-class
            # for janus, the same pattern remote.serve()'s worker runs:
            # the fast calling convention holds here and per-call attach
            # cost is gone. janus.engine() names this engine to
            # thread_signal, the address interrupt() throws at; a startup
            # failure is delivered to the awaiting start(), never hung on.
            janus = bridge()
            try:
                janus.attach_engine()
                swi_thread = janus.engine()
            except BaseException as exc:
                # Bind to an ordinary local: Python deletes the except
                # target when the block exits, and the deferred lambda
                # would find the name unbound instead of the exception.
                with self._state_lock:
                    self._fail_locked(exc)
                logger.exception("AsyncMeTTa worker could not attach its engine")
                failure = exc
                try:
                    loop.call_soon_threadsafe(_set_future_exception, started, failure)
                finally:
                    _forget_worker(self)
                return
            with self._state_lock:
                # Publish the engine id under the same lock and before the
                # live state that lets submit() accept a request.
                self._swi_thread = swi_thread
                if self._state == "starting":
                    self._state = "live"
            logger.debug("AsyncMeTTa worker attached a Prolog engine")
            try:
                try:
                    loop.call_soon_threadsafe(_set_future_result, started)
                except RuntimeError:
                    # The awaiting caller's loop closed while this engine was
                    # attaching. There is nobody to report to and nobody left
                    # to stop this worker either, so it refuses itself instead
                    # of raising out of the thread and then blocking forever on
                    # a queue no one will feed
                    # [tested test_aio_a_worker_whose_loop_closed_stops_itself].
                    logger.warning(
                        "could not report AsyncMeTTa worker startup: event loop closed"
                    )
                    self.close_soon()
                while True:
                    request = self.work.get()
                    if request is None:
                        return
                    if request.abandoned.is_set():
                        continue  # cancelled while queued: never runs
                    with self._transition:
                        with self._state_lock:
                            closing = self._state == "closing"
                        if closing:
                            request.abandoned.set()
                        else:
                            self._current = request
                    if closing:
                        _deliver(
                            request,
                            MettaError("AsyncMeTTa closed before this request ran"),
                            failed=True,
                        )
                        continue
                    try:
                        result = request.context.run(request.fn, request.target)
                    except BaseException as exc:  # noqa: BLE001
                        # Base exceptions cross to the awaiting task too.
                        outcome, failed = exc, True
                    else:
                        outcome, failed = result, False
                    finally:
                        with self._transition:
                            self._current = None
                            drain_failure: BaseException | None = None
                            try:
                                self._drain()
                            except BaseException as exc:  # noqa: BLE001
                                # The request future must resolve even when a
                                # process-level exception breaks the barrier.
                                drain_failure = exc
                    if drain_failure is not None:
                        if failed and isinstance(outcome, BaseException):
                            outcome = BaseExceptionGroup(
                                "the request and its transition drain both failed",
                                [outcome, drain_failure],
                            )
                        else:
                            outcome = drain_failure
                        failed = True
                    _deliver(request, outcome, failed=failed)
                    if drain_failure is not None:
                        self._fail_worker(drain_failure)
                        return
            finally:
                try:
                    janus.detach_engine()
                except Exception as exc:
                    # Any detachment failure makes the worker unusable.
                    with self._state_lock:
                        self._swi_thread = None
                        self._fail_locked(exc)
                    logger.exception("AsyncMeTTa worker could not detach its engine")
                else:
                    with self._state_lock:
                        self._swi_thread = None
                        if self._state == "closing":
                            self._state = "closed"
                        elif self._state == "live":
                            self._fail_locked(
                                RuntimeError("the worker thread stopped unexpectedly")
                            )
                    logger.debug("AsyncMeTTa worker detached its Prolog engine")
                _forget_worker(self)

        self.thread = threading.Thread(target=worker, name="metta-aio", daemon=True)
        logger.debug("starting AsyncMeTTa worker thread")
        _remember_worker(self)
        try:
            self.thread.start()
        except BaseException as exc:
            _forget_worker(self)
            with self._state_lock:
                self._fail_locked(exc)
            raise
        try:
            await asyncio.shield(started)
        except asyncio.CancelledError:
            # This call launched the worker, so nothing else will ever stop
            # it: connect() never returned a handle and the awaiting caller
            # is gone. Refuse it here and the thread detaches its engine on
            # its own, instead of living to interpreter exit
            # [tested test_aio_cancelled_connect_leaves_no_live_worker].
            started.add_done_callback(_retrieve_startup)
            self.close_soon()
            raise

    def _fail_locked(self, cause: BaseException) -> None:
        self._failure = cause
        self._state = "failed"
        logger.error(
            "AsyncMeTTa worker entered failed state: %s: %s",
            type(cause).__name__,
            cause,
        )

    def _raise_state_locked(self) -> None:
        if self._state == "failed":
            cause = self._failure
            detail = f": {type(cause).__name__}: {cause}" if cause is not None else ""
            msg = f"AsyncMeTTa worker failed{detail}"
            raise MettaError(msg) from cause
        msg = f"AsyncMeTTa worker is {self._state}"
        raise MettaError(msg)

    def _fail_worker(self, cause: BaseException) -> None:
        pending: list[_Request] = []
        with self._state_lock:
            self._fail_locked(cause)
            while True:
                try:
                    request = self.work.get_nowait()
                except queue.Empty:
                    break
                if request is not None:
                    pending.append(request)
        for request in pending:
            failure = MettaError(
                f"AsyncMeTTa worker failed before this request ran: {type(cause).__name__}: {cause}"
            )
            failure.__cause__ = cause
            _deliver(request, failure, failed=True)
        if pending:
            logger.error("rejected %d queued request(s) after worker failure", len(pending))

    def submit(self, request: _Request) -> None:
        with self._state_lock:
            if self._state == "live" and self.thread is not None:
                if not self.thread.is_alive():
                    self._fail_locked(RuntimeError("the worker thread stopped"))
                else:
                    self.work.put(request)
                    return
            self._raise_state_locked()

    def _drain(self) -> None:
        # One no-op engine call: a thread_signal throw that raced the end
        # of its goal fires here, inside the transition lock, and is
        # discarded as the stale stop it is.
        janus = bridge()
        try:
            janus.query_once("true")
        except janus.PrologError as exc:
            try:
                runtime()._raise(exc)
            except Interrupted:
                logger.debug("discarded a stale AsyncMeTTa interrupt: %s", exc)

    def interrupt_if_running(self, request: _Request | None) -> bool:
        """Signal the engine thread if `request` is the one running now,
        or if anything is running when request is None. Answers whether a
        signal was sent.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        with self._state_lock:
            swi_thread = self._swi_thread
        with self._transition:
            current = self._current
            if current is None or (request is not None and current is not request):
                return False
            if swi_thread is None:
                msg = "the async worker has a request but no published Prolog engine"
                raise RuntimeError(
                    msg
                )
            # query_once is safe from a bare foreign thread (the loop's),
            # and this bypasses the runtime lock on purpose: the running
            # goal holds that lock, and the signal is how it lets go.
            bridge().query_once(
                "thread_signal(T, throw(error(metta_control_signal(interrupted, none), "
                "context(metta, interrupted))))",
                {"T": swi_thread},
            )
            logger.debug("sent an interrupt to the AsyncMeTTa worker")
            return True

    def close_soon(self) -> threading.Thread | None:
        pending: list[_Request] = []
        with self._state_lock:
            if self._state == "unstarted":
                self._state = "closed"
                return None
            if self._state == "failed":
                self._state = "closed"
                return self.thread
            if self._state == "closed":
                return self.thread
            if self._state != "closing":
                self._state = "closing"
                while True:
                    try:
                        queued = self.work.get_nowait()
                    except queue.Empty:
                        break
                    if queued is not None:
                        queued.abandoned.set()
                        pending.append(queued)
                self.work.put(None)
            thread = self.thread
        for request in pending:
            _deliver(
                request,
                MettaError("AsyncMeTTa closed before this request ran"),
                failed=True,
            )
        if pending:
            logger.debug("rejected %d queued AsyncMeTTa request(s)", len(pending))
        return thread

    def stop(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronously stop this worker and detach its Prolog engine."""
        timeout = _close_timeout(timeout)
        thread = self.close_soon()
        if thread is None or not thread.is_alive():
            return
        if thread is threading.current_thread():
            msg = "an AsyncMeTTa worker cannot stop itself"
            raise MettaError(msg)
        self.interrupt_if_running(None)
        thread.join(timeout)
        if thread.is_alive():
            self.interrupt_if_running(None)
            logger.error("AsyncMeTTa worker exceeded its stop timeout")
            msg = f"AsyncMeTTa worker did not stop within {timeout:g} seconds"
            raise TimeoutError(
                msg
            )

    @property
    def state(self) -> str:
        with self._state_lock:
            if (
                self._state == "live"
                and self.thread is not None
                and not self.thread.is_alive()
            ):
                self._fail_locked(RuntimeError("the worker thread stopped"))
            return self._state


def _close_timeout(timeout: float) -> float:
    value = float(timeout)
    if not math.isfinite(value) or value <= 0:
        msg = f"close timeout must be finite and positive, got {timeout!r}"
        raise ValueError(msg)
    return value


def _remember_worker(worker: _EngineThread) -> None:
    with _LIVE_WORKERS_LOCK:
        _LIVE_WORKERS.add(worker)


def _forget_worker(worker: _EngineThread) -> None:
    with _LIVE_WORKERS_LOCK:
        _LIVE_WORKERS.discard(worker)


def _shutdown_workers() -> None:
    with _LIVE_WORKERS_LOCK:
        workers = tuple(_LIVE_WORKERS)
    if not workers:
        return
    logger.debug("stopping %d AsyncMeTTa worker(s) at exit", len(workers))
    failures: list[Exception] = []
    shutdown_errors = (
        MettaError,
        RuntimeError,
        TimeoutError,
        bridge().PrologError,
    )
    for worker in workers:
        try:
            worker.stop()
        except shutdown_errors as exc:
            failures.append(exc)
    if failures:
        msg = f"failed to stop {len(failures)} AsyncMeTTa worker(s) at exit"
        raise ExceptionGroup(
            msg,
            failures,
        )


atexit.register(_shutdown_workers)


async def _settled(task: asyncio.Task[Any]) -> BaseException | None:
    """Wait for `task` to finish, and answer the failure it ended with.

    The wait survives repeated cancellation of the waiter.
    Cancelling the waiter is not cancelling the work: `task` is the
    acquisition or the release that has to finish whatever happens to the
    coroutine waiting on it, so a cancel landing here is absorbed and the
    wait resumes. A caller re-raises its own cancellation afterwards; this
    answers only what the work itself did. The loop is the one
    AsyncSaga.__aenter__ has run since its cancellation cleanup was written,
    lifted here so every acquisition on this worker shares it.
    """
    while not task.done():
        with contextlib.suppress(BaseException):
            await asyncio.shield(task)
    return None if task.cancelled() else task.exception()


async def _acquire[T](
    work: Coroutine[Any, Any, T],
    release: Callable[[T], Coroutine[Any, Any, Any]],
) -> T:
    """Acquire on the worker, and release what a cancelled caller cannot own.

    Cancelling around an acquisition is the torn middle: the worker finishes
    attaching the engine, registering the subscription or installing the
    facts, and _deliver drops the result because the awaiting future is
    already cancelled, so the resource is live with nothing holding it
    [measured 2026-08-30: one leaked worker thread, one invisible live
    subscription and one permanently installed fact, one per cancelled
    acquisition; tested test_aio_cancelled_connect_leaves_no_live_worker,
    test_aio_cancelled_subscription_registration_cancels_it,
    test_aio_cancelled_assuming_removes_the_facts_it_installed].
    The commit point is shielded so the acquisition always completes, and the
    cancelled caller then releases what it can no longer own before the
    CancelledError continues.
    """
    acquiring = asyncio.ensure_future(work)
    try:
        return await asyncio.shield(acquiring)
    except asyncio.CancelledError:

        async def undo() -> None:
            try:
                acquired = await acquiring
            except BaseException:  # noqa: BLE001  -- an acquisition that failed holds nothing to release
                return
            await release(acquired)

        failure = await _settled(asyncio.ensure_future(undo()))
        if failure is not None:
            # Not logger.exception: the failure worth reading is the release's,
            # not the CancelledError this handler was entered with.
            logger.error(  # noqa: TRY400  -- the handled exception is the cancellation, and the release's failure is what this reports
                "could not release an abandoned AsyncMeTTa acquisition",
                exc_info=failure,
            )
        raise


async def _shielded(work: Coroutine[Any, Any, Any]) -> None:
    """Complete a release even when this task is cancelled.

    The cancellation continues afterwards. A close torn in half leaves the
    engine's resource live while the flag that would refuse a retry is already
    set.
    """
    releasing = asyncio.ensure_future(work)
    try:
        await asyncio.shield(releasing)
    except asyncio.CancelledError:
        failure = await _settled(releasing)
        if failure is not None:
            logger.error(  # noqa: TRY400  -- the handled exception is the cancellation, and the release's failure is what this reports
                "an AsyncMeTTa release failed after its caller was cancelled",
                exc_info=failure,
            )
        raise


def _retrieve_startup(startup: asyncio.Future[None]) -> None:
    """Consume a startup outcome no coroutine waits for any more.

    An abandoned attach failure then does not surface as an unretrieved
    exception.
    """
    if not startup.cancelled():
        startup.exception()


def _deliver(request: _Request, payload, *, failed: bool) -> None:
    def resolve() -> None:
        if request.future.done():  # the awaiting task was cancelled
            return
        if failed:
            request.future.set_exception(payload)
        else:
            request.future.set_result(payload)

    try:
        request.loop.call_soon_threadsafe(resolve)
    except RuntimeError:
        # The loop closed while the engine worked: the coroutine that
        # asked no longer exists, so there is nowhere to deliver to.
        logger.warning("could not deliver an AsyncMeTTa result: event loop closed")


class AsyncMeTTa:
    """A space whose calls are awaited instead of blocking.

        async with metta.aio.connect() as am:
            await am.add(S.edge(1, 2))
            rows = await am.match(S.edge(V.a, V.b))

    The rule: every finite request-response method forwards through the
    worker; context managers, cursors, decorators, callback registrations,
    returned synchronous helper objects and interactive entry points remain
    call() or synchronous-surface operations.

    call(fn) reaches anything not mirrored by running fn(m) on the engine's
    thread. interrupt() stops the evaluation the
    worker is running right now, and cancelling a waiting task (an
    asyncio timeout included) interrupts its own call, so the engine
    stops working for a listener that is gone.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        space: str | Symbol | Expression | Space = _DEFAULT_SPACE,
        *,
        metta: Space | None = None,
    ) -> None:
        self._m = metta if metta is not None else Space(space)
        self._worker = _EngineThread()
        self._closed = False
        self._owner = True

    @classmethod
    def _sharing(cls, metta: Space, worker: _EngineThread) -> AsyncMeTTa:
        shared = cls.__new__(cls)
        shared._m = metta
        shared._worker = worker
        shared._closed = False
        shared._owner = False
        return shared

    @property
    def name(self) -> _SpaceId:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return self._m.name

    @property
    def dropped(self) -> bool:
        """Whether drop() has released the wrapped space's handle."""
        return self._m.dropped

    def bind(
        self,
        values: Mapping[str, Any] | None = None,
        /,
        **named: Any,
    ) -> Any:
        """Scope host values copied into subsequent worker requests."""
        return self._m.bind(values, **named)

    @property
    def metta(self) -> Space:
        """The wrapped synchronous space, for engine-thread work via call()."""
        return self._m

    async def start(self) -> Self:
        """Start the engine thread; connect() and `async with` call this."""
        if self._closed:
            msg = "this AsyncMeTTa is closed"
            raise MettaError(msg)
        await self._worker.start()
        return self

    async def call(self, fn: Callable[[Space], Any]) -> Any:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self._closed:
            msg = "this AsyncMeTTa is closed"
            raise MettaError(msg)
        await self._worker.start()
        loop = asyncio.get_running_loop()
        request = _Request(fn, self._m, loop, loop.create_future())
        self._worker.submit(request)
        try:
            return await request.future
        except asyncio.CancelledError:
            # The listener is gone; stop the engine working for it. A
            # request still queued is skipped, a running one is signalled.
            request.abandoned.set()
            self._worker.interrupt_if_running(request)
            raise

    def interrupt(self) -> bool:
        """Stop the evaluation the worker is running right now; answers
        whether anything was running (idle is a no-op, sqlite3's own
        reading). The stopped call raises metta.Interrupted; whatever it
        completed before the stop, writes included, stands. Callable from
        any thread or task.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._worker.interrupt_if_running(None)

    # ------------------------------------------------------- mirrored surface

    async def run(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Run MeTTa source on the worker and return its result groups."""
        return await self.call(
            lambda m: m.run(source, timeout=timeout, inferences=inferences)
        )

    async def load(
        self,
        path: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list:
        """Load source or a fast cache into this space on the worker."""
        return await self.call(
            lambda m: m.load(path, timeout=timeout, inferences=inferences)
        )

    async def save(self, path: str, format: SaveFormat = SaveFormat.metta) -> int:  # noqa: A002  -- format is the documented public save keyword and must remain compatible
        """Save this space and return the number of stored atoms."""
        return await self.call(lambda m: m.save(path, format=format))

    async def add(self, *atoms: Any) -> None:
        """Add atoms to this space on the worker."""
        return await self.call(lambda m: m.add(*atoms))

    async def remove(self, atom: Any) -> bool:
        """Remove one matching atom and report whether one existed."""
        return await self.call(lambda m: m.remove(atom))

    async def clear(self) -> None:
        """Remove every atom from this space."""
        return await self.call(lambda m: m.clear())

    async def count(self) -> int:
        """Return the number of atoms in this space."""
        return await self.call(len)

    async def atoms(self) -> list:
        """Return a snapshot of every atom in this space."""
        return await self.call(lambda m: m.atoms())

    async def peek(
        self, pattern: Any, *, where: Any | None = None, deadline: float | None = None
    ) -> Atom:
        """Wait for one matching atom without blocking the event loop."""
        return await self.call(
            lambda m: m.peek(pattern, where=where, deadline=deadline)
        )

    async def take(
        self, pattern: Any, *, where: Any | None = None, deadline: float | None = None
    ) -> Atom:
        """Wait for and remove one matching atom without blocking the loop."""
        return await self.call(
            lambda m: m.take(pattern, where=where, deadline=deadline)
        )

    async def match(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        into: _builtins.type | None = None,
    ) -> Any:
        """Match patterns with synchronous bounds, carrier, guard, and shape.

        ``under=`` is resolved in the caller's copied ContextVar context and
        executed on the owning worker, so a surrounding ``metta.under``
        scope behaves the same across the async hop.
        """
        return await self.call(
            lambda m: m.match(
                *patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                under=under,
                into=into,
            )
        )

    async def solve(self, pattern: Any, subject: Any) -> Any:
        """Solve a relation backwards and return caller-named bindings."""
        return await self.call(lambda m: m.solve(pattern, subject))

    async def eval(
        self,
        target: Any,
        *,
        using: dict[str, Any] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
        theory: Any | None = None,
        interpreter: Any | None = None,
    ) -> list[Atom]:
        """Evaluate a term and return every answer.

        `under`, `theory` and `interpreter` are the synchronous eval()'s, and
        they matter more here: answers() is excluded from this surface because
        a replayable cross-thread iterator is not what an await gives you, so
        without them there was no way to annotate an EVALUATION asynchronously
        at all -- match(under=) covered patterns and nothing covered calls
        [measured 2026-08-31].
        """
        carrier = _selected_under(under)
        return await self.call(
            lambda m: m.eval(
                target,
                using=using,
                timeout=timeout,
                inferences=inferences,
                under=_UNSET if carrier is None else carrier,
                theory=theory,
                interpreter=interpreter,
            )
        )

    async def one(
        self,
        target: Any,
        *,
        using: dict[str, Any] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """Evaluate a term that must produce exactly one value."""
        return await self.call(
            lambda m: m._one(
                target,
                using=using,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def copy(self) -> AsyncMeTTa:
        """This space's contents in a new anonymous space; Space.copy,
        the clone borrowing this connection's worker.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        clone = await self.call(lambda m: m.copy())
        return AsyncMeTTa._sharing(clone, self._worker)

    async def reify(self) -> AsyncWorld:
        """Capture one immutable world on the owning engine worker."""
        world = await self.call(lambda m: m.reify())
        return AsyncWorld(self, world)

    async def commit(self, world: AsyncWorld) -> None:
        """Commit an async world through the worker that produced it."""
        if not isinstance(world, AsyncWorld):
            msg = f"commit expects an AsyncWorld, got {type(world).__name__}"
            raise TypeError(msg)
        if world._am._worker is not self._worker:
            msg = "an async world must be committed through its originating engine worker"
            raise MettaError(msg)
        await self.call(lambda m: m.commit(world._world))

    async def covers(self, effect: EffectClass | str) -> Atom:
        """Declare reified-world effect coverage on the owning worker."""
        return await self.call(lambda m: m.covers(effect))

    async def compensates(self, operation: str, compensation: str) -> Atom:
        """Declare one saga compensation on the owning worker."""
        return await self.call(lambda m: m.compensates(operation, compensation))

    def saga(self, receipts: AsyncMeTTa) -> AsyncSaga:
        """Open an async saga whose complete scopes run on this worker."""
        if not isinstance(receipts, AsyncMeTTa):
            msg = (
                "async saga receipts must be an AsyncMeTTa, got "
                f"{type(receipts).__name__}"
            )
            raise TypeError(msg)
        if receipts._worker is not self._worker:
            msg = "an async saga and its receipt space must share one engine worker"
            raise MettaError(msg)
        return AsyncSaga(self, receipts)

    async def drop(self) -> None:
        """Drop this named space from the engine."""
        return await self.call(lambda m: m.drop())

    async def profile(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """Profile source execution and return its groups and counters."""
        return await self.call(
            lambda m: m.profile(source, using, timeout=timeout, inferences=inferences)
        )

    async def parse(self, source: str) -> Any:
        """Parse one MeTTa term without evaluating it."""
        return await self.call(lambda m: m.parse(source))

    async def register_token(
        self,
        pattern: str | _re.Pattern[str],
        constructor: Callable[[str], Any],
    ) -> None:
        """Register a full-lexeme reader class on the engine worker."""
        return await self.call(lambda m: m.register_token(pattern, constructor))

    async def unregister_token(self, pattern: str | _re.Pattern[str]) -> None:
        """Remove a reader class from the engine worker."""
        return await self.call(lambda m: m.unregister_token(pattern))

    @overload
    async def cast(self, value: Any, type_: _builtins.type[_CastT], /) -> _CastT: ...

    @overload
    async def cast(self, value: Any, type_: Atom | str, /) -> Any: ...

    async def cast(self, value: Any, type_: Any, /) -> Any:
        """Check and narrow a value through the engine type system."""
        return await self.call(lambda m: m.cast(value, type_))

    async def trace(self, source: str, max_events: int = 1_000_000) -> Any:
        """Trace source execution up to the requested event bound."""
        return await self.call(lambda m: m.trace(source, max_events=max_events))

    async def lint(self) -> Any:
        """Return static findings for this space."""
        return await self.call(lambda m: m.lint())

    async def digest(self) -> str:
        """Return the stable content digest for this space."""
        return await self.call(lambda m: m.digest())

    async def unregister_op(self, name: str) -> None:
        """Remove every registered operation overload under a name."""
        return await self.call(lambda m: m.unregister_op(name))

    async def builtins(self) -> list[str]:
        """Return the names of engine builtins."""
        return await self.call(lambda m: m.builtins())

    async def is_function(self, name: str) -> bool:
        """Report whether a function is visible from this space."""
        return await self.call(lambda m: m.is_function(name))

    async def is_function_here(self, name: str) -> bool:
        """Report whether this space defines a function itself."""
        return await self.call(lambda m: m.is_function_here(name))

    async def arities(self, name: str) -> list[int]:
        """Return the registered arities for a function name."""
        return await self.call(lambda m: m.arities(name))

    async def derivation(
        self,
        target: Any,
        depth: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """Build a bounded derivation tree for one target."""
        return await self.call(
            lambda m: m.derivation(
                target,
                depth=depth,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def reducible(self, target: Any) -> bool:
        """Whether a head reduces here, asked without evaluating anything."""
        return await self.call(lambda m: m.reducible(target))

    async def why(self, pattern: Any, *, where: Any | None = None) -> str:
        """Explain why a pattern is not currently reducible."""
        return await self.call(lambda m: m.why(pattern, where=where))

    async def space(
        self,
        name: str | None = None,
        backing: Any = None,
        *,
        inherits: AsyncMeTTa | None = None,
        restricted: bool = False,
        grants: Sequence[str] = (),
    ) -> AsyncMeTTa:
        """Create or open one space through this connection's worker.

        An omitted name creates an anonymous space. A provider supplied as
        ``backing`` is attached to the resulting handle. The connection owns
        the worker; returned spaces borrow it, so closing one does not stop
        the connection.
        """
        if inherits is not None and inherits._worker is not self._worker:
            msg = "an inherited async space must share this engine worker"
            raise ValueError(msg)
        if name is not None and (inherits is not None or restricted or grants):
            msg = "inherits, restricted, and grants apply only to anonymous space()"
            raise TypeError(msg)
        if name is None:
            parent = None if inherits is None else inherits._m
            requested_grants = tuple(grants)
            created_at = _creation_site()
            handle = await self.call(
                lambda m: m._new_space(
                    inherits=parent,
                    restricted=restricted,
                    grants=requested_grants,
                    _created_at=created_at,
                )
            )
        else:
            handle = await self.call(lambda m: m._at(name))
        if backing is not None:
            await self.call(lambda m: m._register_space(backing, str(handle.name)))
            handle._backing = backing
        return AsyncMeTTa._sharing(handle, self._worker)

    # ----------------------------------------------------- parity delegations
    # One worker round trip each, the synchronous surface's own docstrings
    # applying verbatim. The deliberate exclusions live in the parity test:
    # pool (asyncio's fan-out is N workers and gather), prolog (an
    # interactive toplevel belongs to a terminal thread), and transactional
    # (a transaction body is a closed synchronous goal; transaction() is
    # the async spelling).

    async def first(
        self,
        target: Any,
        *,
        using: dict[str, Any] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """The first answer decoded, or None for no answers."""
        return await self.call(
            lambda m: m._first(
                target, using=using, timeout=timeout, inferences=inferences
            )
        )

    async def parallel(self, *targets: Any, timeout: float | None = None) -> list:
        """Evaluate every target concurrently inside the engine."""
        return await self.call(lambda m: m.parallel(*targets, timeout=timeout))

    async def hyperpose(self, *targets: Any, timeout: float | None = None) -> list:
        """parallel() under its MeTTa name."""
        return await self.call(lambda m: m.hyperpose(*targets, timeout=timeout))

    async def integrate(self, target: Any) -> str:
        """Install a library integration; see metta.integrate."""
        return await self.call(lambda m: m.integrate(target))

    async def profile_extension(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        extension: str | None = None,
        names: Sequence[str] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple:
        """Run source and report per-function engine cost."""
        return await self.call(
            lambda m: m.profile_extension(
                source,
                using,
                extension=extension,
                names=names,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def eval_status(
        self,
        target: Any,
        *,
        using: dict[str, Any] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list:
        """Evaluate and report each answer's outcome kind."""
        return await self.call(
            lambda m: m.eval_status(
                target, using=using, timeout=timeout, inferences=inferences
            )
        )

    async def run_status(
        self,
        source: str,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list:
        """Run source and report each directive's outcome kinds."""
        return await self.call(
            lambda m: m.run_status(source, timeout=timeout, inferences=inferences)
        )

    async def space_names(self) -> list[str]:
        """Every space name this engine registers, sorted."""
        return await self.call(lambda m: m.space_names())

    async def admits(self, type_name: str) -> Atom:
        """Declare an admitted type on the owning engine worker."""
        return await self.call(lambda m: m.admits(type_name))

    async def annotations(
        self,
        subject_or_algebra: str,
        algebra: str | None = None,
        *,
        capabilities: Sequence[str] = (),
    ) -> Atom:
        """Declare annotation algebra or subject capabilities on the worker."""
        return await self.call(
            lambda m: m.annotations(
                subject_or_algebra, algebra, capabilities=capabilities
            )
        )

    async def algebra(
        self,
        name: str,
        *,
        combine: str,
        extend: str,
        zero: Any,
        one: Any,
        laws: Sequence[str] = (),
        carrier: Sequence[Any] = (),
        requires: Sequence[str] = (),
        order: SemiringOrder | None = None,
    ) -> Atom:
        """Declare one checked value algebra on the owning engine thread."""
        return await self.call(
            lambda m: m.algebra(
                name,
                combine=combine,
                extend=extend,
                zero=zero,
                one=one,
                laws=laws,
                carrier=carrier,
                requires=requires,
                order=order,
            )
        )

    async def add_tagged_fact(self, tag: Any, proposition: Any) -> Atom:
        """Store one ordinary tagged fact on the owning engine thread."""
        return await self.call(lambda m: m.add_tagged_fact(tag, proposition))

    async def add_tagged_rule(
        self, tag: Any, head: Any, *premises: Any
    ) -> Atom:
        """Store one algebra-threaded ordinary rule on the owning engine thread."""
        return await self.call(
            lambda m: m.add_tagged_rule(tag, head, *premises)
        )

    async def sample(
        self,
        query: str | Atom,
        *,
        k: int = 10,
        seed: int = 7,
    ) -> list[Atom]:
        """Draw ``k`` rate-weighted choices on the owning engine thread."""
        return await self.call(
            lambda m: m.sample(query, k=k, seed=seed)
        )

    async def capacity(self, limit: int) -> Atom:
        """Declare the maximum concurrent work for this context."""
        return await self.call(lambda m: m.capacity(limit))

    async def context(self, world: World) -> Atom:
        """Declare whether this context uses an open or closed world."""
        return await self.call(lambda m: m.context(world))

    async def emits(self, policy: AnswerPolicy) -> Atom:
        """Declare this context's answer emission policy."""
        return await self.call(lambda m: m.emits(policy))

    async def events(
        self,
        delivery: Delivery | None = None,
        order: EventOrder = EventOrder.unordered,
    ) -> Any:
        """Return the event stream or declare this context's event promise.

        A fold registered through it runs on the engine thread, inside the
        write that caused the event, exactly as a synchronous one does.
        `AsyncMeTTa.subscribe` is the async-native door for the delivering
        fold and hands events to an async iterator instead.
        """
        return await self.call(
            lambda m: m.events() if delivery is None else m.events(delivery, order)
        )

    async def handles(
        self,
        pattern: str | Atom,
        fidelity: Fidelity,
        *,
        det: Determinism | None = None,
    ) -> Atom:
        """Declare a handler's pattern, fidelity, and determinism."""
        return await self.call(
            lambda m: m.handles(pattern, fidelity, det=det)
        )

    async def image(
        self,
        type_name: str,
        setting: ImageMode,
    ) -> Atom:
        """Declare whether one type crosses by value or identity."""
        return await self.call(
            lambda m: m.image(type_name, setting)
        )

    async def merge(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, pattern: str | Atom, policy: AnswerPolicy
    ) -> Atom:
        return await self.call(lambda m: m.merge(pattern, policy))

    async def on_error(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        subject_or_pattern: str | Atom,
        pattern_or_mode: str | Atom,
        mode: OnError | None = None,
    ) -> Atom:
        return await self.call(
            lambda m: m.on_error(subject_or_pattern, pattern_or_mode, mode)
        )

    async def reacts(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        pattern: str | Atom,
        operation: str | Atom,
        priority: int | None = None,
    ) -> Atom:
        return await self.call(
            lambda m: m.reacts(pattern, operation, priority)
        )

    async def reaction(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        pattern: str | Atom,
        operation: str | Atom,
        priority: int | None = None,
    ) -> Atom:
        return await self.reacts(pattern, operation, priority)

    async def agenda(
        self, policy: AgendaPolicy, function: str | None = None
    ) -> Atom:
        """Declare which reaction fires first; see Space.agenda."""
        return await self.call(lambda m: m.agenda(policy, function))

    async def source(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, kind: SourceKind
    ) -> Atom:
        return await self.call(lambda m: m.source(kind))

    async def atomicity(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        atomicity: Atomicity,
    ) -> Atom:
        return await self.call(lambda m: m.atomicity(atomicity))

    async def op(
        self,
        fn: Callable,
        /,
        *,
        effect: EffectClass | str,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Callable:
        """Register a callable through the single short operation door."""
        options: dict[str, Any] = {
            "name": name,
            "transport": transport,
            "effect": effect,
            "declarations": declarations,
            "arities": arities,
            "inverse": inverse,
        }
        return await self.call(
            lambda m: m.op(fn, **options)
        )

    # The four effect faces of `op`, mirroring Space so the async surface is
    # the same surface. Each awaits the registration on the engine thread.

    async def pure(self, fn: Callable, /, **options: Any) -> Callable:
        """An operation whose answer depends only on its arguments."""
        return await self.call(lambda m: m.pure(fn, **options))

    async def reads(self, fn: Callable, /, **options: Any) -> Callable:
        """An operation that reads stable state without changing it."""
        return await self.call(lambda m: m.reads(fn, **options))

    async def writes(self, fn: Callable, /, **options: Any) -> Callable:
        """An operation that changes engine or host state."""
        return await self.call(lambda m: m.writes(fn, **options))

    async def io(self, fn: Callable, /, **options: Any) -> Callable:
        """An operation that observes an external oracle."""
        return await self.call(lambda m: m.io(fn, **options))

    async def cache(
        self,
        fn: Callable | None = None,
        /,
        *,
        name: str | None = None,
        unchecked: bool = False,
    ) -> Any:
        """Define and memoize on the worker, the sync door's cache decorator.

        The memo stores every answer occurrence, and the returned handle
        carries cache_clear() and cache_info() as synchronous doors the way
        define's handle carries its own.
        """
        if fn is None:
            msg = "cache takes a function"
            raise TypeError(msg)
        function = fn
        return await self.call(
            lambda m: m.cache(name=name, unchecked=unchecked)(function)
        )

    async def rules(self, fn: Callable) -> Any:
        """Collect and land a non-exclusive equation bundle on the worker.

        An awaitable CALL rather than a decorator, which is the same answer
        define() gives to the same problem: decoration cannot await, so the
        door stops being a decorator instead of stopping existing. It was
        excluded from the async surface for the first reading of that, which
        left an async caller unable to land a bundle at all
        [measured 2026-08-31].
        """
        return await self.call(lambda space: space.rules(fn))

    async def pre_add(self, fn: Callable) -> Any:
        """Compile or accept one unary judge and claim this space's write door.

        Excluded for the same reading as rules(), and restored the same way.
        """
        return await self.call(lambda space: space.pre_add(fn))

    async def define(
        self,
        fn: Callable | None = None,
        /,
        *,
        prolog: str | os.PathLike[str] | None = None,
        name: str | None = None,
        accessors: bool = True,
        methods: bool = True,
    ) -> Any:
        """Compile a Python function into equations on the worker. The
        returned handle's own calls are synchronous doors; evaluate
        through fn(name) or run() from async code.

        `name=` is the naming ladder's exact-spelling rung, and it is here
        because the ladder does not shrink from one surface to another: an
        async caller installing `prime?` or an authored underscore had no
        door for it while the synchronous define did [measured 2026-08-31].
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if fn is not None:
            # accessors= and methods= carry for every shape, their defaults
            # being what the plain call already meant.
            return await self.call(
                lambda m: m.define(
                    fn, name=name, accessors=accessors, methods=methods
                )
            )
        if prolog is None:
            msg = "define takes a function or prolog= source"
            raise TypeError(msg)
        source = prolog
        return await self.call(lambda m: m.define(prolog=source))

    async def type(self, atom: Any, /) -> Atom:
        """Return this space's first get-type answer on the worker."""
        return await self.call(lambda m: m.type(atom))

    async def doc(self, atom: Any, /) -> Atom:
        """Return this space's structured get-doc answer on the worker."""
        return await self.call(lambda m: m.doc(atom))

    async def register_prolog(
        self,
        source: str | None = None,
        *,
        path: str | os.PathLike[str] | None = None,
        names: Sequence[str] | Mapping[str, str] = (),
    ) -> tuple[str, ...]:
        """Register Prolog predicates as MeTTa functions."""
        return await self.call(
            lambda m: m.register_prolog(source, path=path, names=names)
        )

    async def register_foreign_library(
        self,
        path: str | os.PathLike[str],
        *,
        entry: str | None = None,
        names: Sequence[str] = (),
    ) -> tuple[str, ...]:
        """Load a foreign library of Prolog predicates."""
        return await self.call(
            lambda m: m.register_foreign_library(path, entry=entry, names=names)
        )

    async def register_library_path(self, directory: Any, name: str) -> None:
        """Register a directory for (library ...) imports."""
        return await self.call(lambda m: m.register_library_path(directory, name))

    async def unregister_prolog(self, extension: str) -> tuple[str, ...]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return await self.call(lambda m: m.unregister_prolog(extension))

    def limits(
        self,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        stack: int | None = None,
    ):
        """Scoped default bounds, the synchronous surface's own block:
        enter and exit only touch a contextvar, so this is an ordinary
        `with` inside async code, and every awaited call in the scope
        carries it to the worker.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._m.limits(timeout=timeout, inferences=inferences, stack=stack)

    def capture(self):
        """Collect awaited run/eval output in an ordinary task-local scope."""
        return self._m.capture()

    def atomic(self):
        """Make each awaited run in the block one engine transaction."""
        return self._m.atomic()

    def speculative(self):
        """Answer awaited runs while discarding their engine writes."""
        return self._m.speculative()

    def batch(self) -> _AsyncBatch:
        """Collect this space's add() calls and cross once at exit,
        the synchronous batch's async twin: `async with am.batch():`.
        The same stated edges apply: reads see the pre-batch space,
        remove and clear refuse, an exception discards.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncBatch(self)

    async def transaction(self, target: Callable[[Space], Any] | Atom | str, /) -> Any:
        """Run a callable or term inside one engine transaction on the worker.

        A callable receives the worker's own
        synchronous MeTTa, because a transaction body is a closed
        synchronous goal (SWI's transaction/1 takes one), which is also
        why there is no async body and no transactional decorator here.
        A raise rolls every engine write back and re-raises as itself. A term
        instead follows the engine law: empty answers roll its writes back.

            await am.transaction(lambda m: m.add(S.fact(1)))
        """
        if isinstance(target, (Atom, str)):
            return await self.call(lambda m: m.transaction(target))
        function = target
        return await self.call(lambda m: m.transaction(lambda: function(m)))

    @property
    def runtime(self) -> Runtime:
        """The engine bridge itself, for callers going under the surface.
        Every call on it blocks the calling thread; from async code, wrap
        such work in call().
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._m.runtime

    def stats(self) -> _AsyncStats:
        """The engine's counters over an async with-block, as deltas.

        async with am.stats() as s:
            await am.match(...)
        s.inferences
        """
        return _AsyncStats(self)

    def assuming(self, *facts: Any) -> _AsyncAssuming:
        """Facts held only inside an async with-block: added on entry,
        removed on exit, exceptions included.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncAssuming(self, facts)

    async def prepare(self, *patterns: Any, where: Any | None = None) -> _AsyncPrepared:
        """A prepared query whose solve() is awaitable; the shape builds
        once on the worker, columns readable without a round trip.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        prepared = await self.call(lambda m: m.prepare(*patterns, where=where))
        return _AsyncPrepared(self, prepared)

    def stream(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
    ) -> _AsyncCursor:
        """match(), pulled asynchronously: one row per worker round trip.

            async with am.stream(S.edge(V.a, V.b)) as rows:
                async for row in rows:
                    ...

        Iterating without the async-with also works; aclose() is then the
        caller's duty, the finalization reading the data model gives
        asynchronous iterators.
        """
        return _AsyncCursor(
            self, patterns, where, timeout, inferences, limit=limit, under=under
        )

    def subscribe(
        self,
        pattern: Any,
        *,
        on: str = "add",
        where: Any | None = None,
        queue_max: int = SUBSCRIPTION_QUEUE_MAX,
    ) -> _AsyncSubscription:
        """A standing query as an async event stream: every matching
        write becomes an Event on an asyncio queue, consumed with
        async-for. The synchronous surface's callback form stays there;
        here the stream IS the delivery.

            async with am.subscribe(S.order(V.id), on="add") as events:
                async for event in events:
                    ...
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncSubscription(self, pattern, on, queue_max, where=where)

    def watch(
        self,
        pattern: Any,
        *,
        on: str = "add",
        where: Any | None = None,
        deadline: float | None = None,
        queue_max: int = SUBSCRIPTION_QUEUE_MAX,
    ) -> _AsyncSubscription:
        """Observe matching writes, raising Timeout after each quiet deadline.

        The synchronous watch()'s meaning, which this door carried the NAME of
        without: it was subscribe() under a second name, same signature and
        same body, so an async caller had no way to say "stop waiting after
        this long" that peek() and take() both give them
        [measured 2026-08-31].
        """
        require_deadline(deadline)
        return _AsyncSubscription(
            self, pattern, on, queue_max, deadline=deadline, where=where
        )

    @property
    def fn(self) -> _AsyncFunctionNamespace:
        """Engine functions as async callables, by attribute or exact name.

        ``m.fn.car_atom`` transliterates underscores to hyphens and
        ``m.fn["=="]`` preserves exact punctuation, the same two doors the
        sync namespace has. Resolution is lazy: the worker is asked when the
        function is awaited, so an unknown name raises there rather than at
        access.
        """
        return _AsyncFunctionNamespace(self)

    # -------------------------------------------------------------- lifecycle

    async def aclose(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Interrupt work, reject queued calls, and detach within timeout."""
        timeout = _close_timeout(timeout)
        self._closed = True
        if not self._owner:
            return
        thread = self._worker.close_soon()
        if thread is not None and thread.is_alive():
            self._worker.interrupt_if_running(None)
            await asyncio.to_thread(thread.join, timeout)
            if thread.is_alive():
                self._worker.interrupt_if_running(None)
                msg = f"AsyncMeTTa worker did not stop within {timeout:g} seconds"
                raise TimeoutError(
                    msg
                )

    def stop(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronous cleanup for code without a running event loop."""
        self._closed = True
        if self._owner:
            self._worker.stop(timeout)

    async def __aenter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return await self.start()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        await self.aclose()

    def __del__(self) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        if (
            getattr(self, "_owner", False)
            and not getattr(self, "_closed", True)
            and (worker := getattr(self, "_worker", None)) is not None
            and worker.thread is not None
            and worker.thread.is_alive()
        ):
            warnings.warn(
                "an open AsyncMeTTa was discarded; use async with, await aclose(), or stop()",
                ResourceWarning,
                source=self,
                stacklevel=2,
            )

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        state = "closed" if self._closed else self._worker.state
        return f"AsyncMeTTa({self._m!r}, {state})"


class AsyncSaga:
    """The awaitable context-manager twin of :class:`metta._saga.Saga`."""

    __slots__ = ("_acquiring", "_am", "_receipts", "_saga")

    def __init__(self, am: AsyncMeTTa, receipts: AsyncMeTTa) -> None:
        """Bind both spaces to the one worker that owns their engine calls."""
        self._am = am
        self._receipts = receipts
        self._saga: Any = None
        self._acquiring = False

    async def __aenter__(self) -> Self:
        """Enter the synchronous saga entirely on the owning worker."""
        if self._saga is not None or self._acquiring:
            msg = "an AsyncSaga context cannot be entered twice"
            raise MettaError(msg)

        acquired: dict[str, Any] = {}

        def enter(space: Space) -> Any:
            saga = space.saga(self._receipts._m)
            acquired["saga"] = saga
            saga.__enter__()
            return saga

        self._acquiring = True
        try:
            self._saga = await self._am.call(enter)
        except BaseException as acquisition_error:  # cancellation owns cleanup too
            def cleanup(_space: Space) -> None:
                saga = acquired.pop("saga", None)
                if saga is not None:
                    saga.close()

            cleanup_error = await _settled(
                asyncio.ensure_future(self._am.call(cleanup))
            )
            if cleanup_error is not None:
                msg = "async saga acquisition and cancellation cleanup both failed"
                raise BaseExceptionGroup(
                    msg,
                    [acquisition_error, cleanup_error],
                ) from None
            raise
        finally:
            self._acquiring = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Recover exceptional exits and preserve failed recovery for retry."""
        saga = self._require_saga("exit")
        await self._am.call(
            lambda _space: saga.__exit__(exc_type, error, traceback)
        )
        self._saga = None

    async def run(self, target: Any) -> list[Atom]:
        """Commit one forward step and its receipt on the owning worker."""
        saga = self._require_saga("run")
        return await self._am.call(lambda _space: saga.run(target))

    async def rollback(self) -> None:
        """Run the pending reverse recovery plan on the owning worker."""
        saga = self._require_saga("rollback")
        await self._am.call(lambda _space: saga.rollback())

    async def aclose(self) -> None:
        """Cancel the synchronous receipt observer on the owning worker."""
        saga = self._require_saga("aclose")
        await self._am.call(lambda _space: saga.close())

    def _require_saga(self, operation: str) -> Any:
        saga = self._saga
        if saga is None:
            msg = f"AsyncSaga.{operation}() requires an active async saga"
            raise MettaError(msg)
        return saga


class AsyncWorld:
    """An immutable world whose evaluation crosses its originating worker."""

    __slots__ = ("_am", "_world")

    def __init__(self, am: AsyncMeTTa, world: Any) -> None:
        """Bind an immutable world value to its originating async owner."""
        self._am = am
        self._world = world

    @property
    def atoms(self) -> tuple[Atom, ...]:
        """Return the frozen atom multiset without an engine crossing."""
        return self._world.atoms

    async def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[Atom], AsyncWorld]:
        """Evaluate on the worker and return answers plus a successor value."""
        world = self._world
        answers, successor = await self._am.call(
            lambda _m: world.eval(target, timeout=timeout, inferences=inferences)
        )
        return answers, AsyncWorld(self._am, successor)

    def diff(self, other: AsyncWorld) -> tuple[list[Atom], list[Atom]]:
        """Return ordered multiset extras between worlds from one worker."""
        if not isinstance(other, AsyncWorld):
            msg = f"an async world diff needs another AsyncWorld, got {type(other).__name__}"
            raise TypeError(msg)
        if other._am._worker is not self._am._worker:
            msg = "async worlds from different engine workers cannot be diffed"
            raise MettaError(msg)
        return self._world.diff(other._world)

    async def aclose(self) -> None:
        """Release this world's retained program image on its worker."""
        world = self._world
        await self._am.call(lambda _m: world.close())

    def __repr__(self) -> str:
        """Return a representation containing the frozen atom multiset."""
        return f"AsyncWorld(atoms={self.atoms!r})"


_EXHAUSTED: Final = object()
_STREAM_CLOSED: Final = object()


class _AsyncStats:
    """Space.stats() as an async context manager: the counters start and
    stop on the worker, and the entered block object carries the deltas.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa) -> None:
        self._am = am
        self._block: Any = None

    async def __aenter__(self) -> Any:
        self._block = await self._am.call(lambda m: m.stats().__enter__())
        return self._block

    async def __aexit__(self, exc_type, exc, tb) -> None:
        block = self._block
        await self._am.call(lambda _m: block.__exit__(None, None, None))


class _AsyncAssuming:
    """MeTTa.assuming() as an async context manager: facts added on
    entry, removed on exit, exceptions included.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa, facts: tuple) -> None:
        self._am = am
        self._facts = facts
        self._cm: Any = None

    async def __aenter__(self) -> AsyncMeTTa:
        facts = self._facts
        am = self._am

        def enter(space: Space) -> Any:
            # Both halves on ONE crossing: a cancellation between building the
            # block and entering it used to leave the facts installed with no
            # block to remove them.
            block = space.assuming(*facts)
            block.__enter__()
            return block

        self._cm = await _acquire(
            am.call(enter),
            lambda block: am.call(lambda _m: block.__exit__(None, None, None)),
        )
        return am

    async def __aexit__(self, exc_type, exc, tb) -> None:
        cm = self._cm
        await self._am.call(lambda _m: cm.__exit__(None, None, None))


class _AsyncPrepared:
    """A Prepared whose solve() is awaitable. The shape lives on the
    worker's engine; columns read without a round trip.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa, prepared: Any) -> None:
        self._am = am
        self._prepared = prepared

    @property
    def columns(self) -> tuple[str, ...]:
        return self._prepared.columns

    async def solve(
        self,
        given: list | None = None,
        limit: int | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Rows:
        """Answers now, with `given` facts present for this call alone."""
        prepared = self._prepared
        return await self._am.call(
            lambda _m: prepared.solve(
                given, limit, timeout=timeout, inferences=inferences
            )
        )

    async def explain(self) -> str:
        """The query's plan, reflected rather than run; Prepared.explain,
        one worker round trip.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        prepared = self._prepared
        return await self._am.call(lambda _m: prepared.explain())

    def __repr__(self) -> str:
        return f"<async prepared query {self.columns} on {self._am.name}>"


class _AsyncCursor:
    """Space.stream() pulled asynchronously: one row per worker round
    trip, closable, and an async context manager. Iterating without the
    async-with works too; aclose() is then the caller's duty, the
    finalization reading the data model gives asynchronous iterators.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am, patterns, where, timeout, inferences, *, limit=None, under=_UNSET) -> None:
        self._am = am
        self._patterns = patterns
        self._where = where
        self._timeout = timeout
        self._inferences = inferences
        self._limit = limit
        self._under = under
        self._cursor: Any = None
        self._closed = False
        self._opening = asyncio.Lock()

    async def _ensure(self) -> Any:
        if self._cursor is not None:
            return self._cursor
        # Two tasks pulling one cursor would otherwise open two engine
        # cursors and keep the second, abandoning the first.
        async with self._opening:
            if self._cursor is None:
                patterns, where = self._patterns, self._where
                timeout, inferences = self._timeout, self._inferences
                limit, under = self._limit, self._under
                am = self._am
                self._cursor = await _acquire(
                    am.call(
                        lambda m: m.stream(
                            *patterns,
                            where=where,
                            limit=limit,
                            timeout=timeout,
                            inferences=inferences,
                            under=under,
                        )
                    ),
                    lambda cursor: am.call(lambda _m: cursor.close()),
                )
            return self._cursor

    async def columns(self) -> tuple[str, ...]:
        """The column names, opening the cursor if it is not yet open."""
        cursor = await self._ensure()
        return cursor.columns

    async def explain(self) -> str:
        """The query's plan, reflected rather than run; Cursor.explain,
        opening the cursor if it is not yet open.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        cursor = await self._ensure()
        return await self._am.call(lambda _m: cursor.explain())

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration
        cursor = await self._ensure()
        row = await self._am.call(lambda _m: next(cursor, _EXHAUSTED))
        if row is _EXHAUSTED:
            await self.aclose()
            raise StopAsyncIteration
        return row

    async def aclose(self) -> None:
        """Close the engine cursor; a failed close stays retryable."""
        if self._closed:
            return
        await _shielded(self._release())

    async def _release(self) -> None:
        # The flag goes up only after the engine cursor is gone: marking
        # first left a live cursor behind a closed flag that refused every
        # retry [tested test_aio_a_failed_cursor_close_stays_retryable].
        cursor = self._cursor
        if cursor is not None:
            await self._am.call(lambda _m: cursor.close())
        self._closed = True

    async def __aenter__(self) -> Self:
        await self._ensure()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()


class _AsyncSubscription:
    """MeTTa.subscribe() as an async event stream: the synchronous
    callback fires on whichever thread wrote and forwards each Event to
    an asyncio queue through call_soon_threadsafe; async-for consumes.
    A class rather than an async generator on purpose: the data model's
    finalization duty for asynchronous generators is exactly what
    aclose() makes explicit here.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(
        self,
        am: AsyncMeTTa,
        pattern: Any,
        on: str,
        queue_max: int = SUBSCRIPTION_QUEUE_MAX,
        *,
        deadline: float | None = None,
        where: Any | None = None,
    ) -> None:
        self._am = am
        self._pattern = pattern
        self._on = on
        self._deadline = deadline
        self._where = where
        # The same bound the synchronous subscription takes, refused here at
        # construction: a bound no comparison decides is not a bound, and
        # asyncio.Queue(maxsize=nan) is a queue that never reports itself full
        # [tested test_the_async_queue_bound_is_refused_the_same_way].
        self._queue_max = _capacity(queue_max)
        self._subscription: Any = None
        self._queue: asyncio.Queue[Any] | None = None
        self._closed = False
        self._dropped = 0
        self._opening = asyncio.Lock()

    def _offer(self, events: asyncio.Queue[Any], event: Any) -> None:
        """Hand one event to a consumer that may have stopped consuming.

        The writer is on another thread and the queue is filled through
        call_soon_threadsafe, so a full queue cannot raise back at whoever
        wrote: by the time this runs the write has returned. What it can do
        is refuse to lose the event quietly. Every event already queued is
        still delivered, and the stream then ends by raising, which is the
        gap being reported rather than papered over.
        """
        try:
            events.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped += 1

    def _end(self, events: asyncio.Queue[Any]) -> None:
        """Wake a consumer blocked on this queue, a full queue included.

        put_nowait raises QueueFull, and raising out of a close path is how a
        subscription stays live behind a closed flag. Closing discards the
        backlog anyway, because __anext__ stops on the closed flag, so one
        queued event makes room for the terminator. A full queue holds at
        least one event and nothing runs between the refused put and this
        get, so the loop ends on its second turn at the latest.
        """
        while True:
            try:
                events.put_nowait(_STREAM_CLOSED)
            except asyncio.QueueFull:
                events.get_nowait()
            else:
                return

    async def _ensure(self) -> asyncio.Queue[Any]:
        if self._queue is not None:
            return self._queue
        # One registration for concurrent consumers, and the queue is
        # published only once one exists to write to it.
        async with self._opening:
            if self._queue is None:
                loop = asyncio.get_running_loop()
                events: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_max)

                def deliver(event: Any) -> None:
                    loop.call_soon_threadsafe(self._offer, events, event)

                pattern, on, am = self._pattern, self._on, self._am
                where = self._where
                self._subscription = await _acquire(
                    am.call(
                        lambda m: m.subscribe(pattern, deliver, on=on, where=where)
                    ),
                    lambda subscription: am.call(lambda _m: subscription.cancel()),
                )
                # A queue reachable before its registration succeeded is one a
                # consumer waits on forever: nothing owns it, and nothing will
                # ever write to it
                # [tested test_aio_a_failed_subscription_publishes_no_queue].
                self._queue = events
            return self._queue

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration
        events = await self._ensure()
        if self._dropped and events.empty():
            # Everything that fit has been delivered; now say what did not.
            dropped, self._dropped = self._dropped, 0
            msg = (
                f"this subscription stream fell {dropped} event(s) behind "
                f"its queue_max of {self._queue_max} and they are gone. "
                f"Consume faster, raise queue_max=, or take the events on "
                f"the synchronous surface, where a full queue refuses the "
                f"write instead of outrunning the reader."
            )
            raise MettaError(
                msg
            )
        if self._deadline is None:
            event = await events.get()
        else:
            try:
                event = await asyncio.wait_for(events.get(), self._deadline)
            except TimeoutError:
                await self.aclose()
                msg = f"no matching change arrived within {self._deadline} seconds"
                raise Timeout(msg) from None
        if event is _STREAM_CLOSED:
            raise StopAsyncIteration
        return event

    async def aclose(self) -> None:
        """Cancel the standing query and end the stream; retryable."""
        if self._closed:
            return
        await _shielded(self._release())

    async def _release(self) -> None:
        # Cancel first: marking closed before the engine let go left a live
        # subscription that every later aclose() returned early from
        # [tested test_aio_a_failed_subscription_close_stays_retryable].
        subscription = self._subscription
        if subscription is not None:
            await self._am.call(lambda _m: subscription.cancel())
        self._closed = True
        if self._queue is not None:
            self._end(self._queue)

    async def __aenter__(self) -> Self:
        await self._ensure()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()


class _AsyncBatch:
    """The batch block's async twin: entering opens the synchronous
    collector in THIS task's context (which every awaited call carries
    to the worker), and a clean exit flushes through one awaited bulk
    crossing.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa) -> None:
        self._am = am
        self._batch = am.metta.batch()

    async def __aenter__(self) -> Self:
        self._batch.__enter__()
        return self

    def __len__(self) -> int:
        return len(self._batch)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        batch = self._batch
        pending = list(batch._pending)
        # Close the collector without flushing on the caller thread ...
        batch._pending = []
        batch.__exit__(exc_type, exc, tb)
        # ... and flush on the worker, where engine calls belong.
        if exc_type is None and pending:
            await self._am.call(lambda m: m.add(*pending))


class _AsyncFunctionNamespace:
    """Functions on one async engine, resolved when the call is awaited."""

    __slots__ = ("_am",)

    def __init__(self, am: AsyncMeTTa) -> None:
        self._am = am

    def __getattr__(self, name: str) -> _AsyncEngineFunction | _AsyncCompositeEngineFunction:
        if name.startswith("_"):
            raise AttributeError(name)
        resolved = operator_attribute_target(name)
        if isinstance(resolved, OperatorRecipe):
            return _AsyncCompositeEngineFunction(self._am, resolved)
        target = name.replace("_", "-") if resolved is None else resolved
        return _AsyncEngineFunction(self._am, target)

    def __getitem__(self, name: str) -> _AsyncEngineFunction:
        if not isinstance(name, str):
            msg = f"an exact function name is a string, got {type(name).__name__}"
            raise TypeError(msg)
        return _AsyncEngineFunction(self._am, name)


class _AsyncEngineFunction:
    """One engine function as an async callable, the cardinality triple
    spelled the same as everywhere: await f(3) is one(), .first
    tolerates absence, .all answers the multiset.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa, name: str) -> None:
        self._am = am
        self._name = name
        self.__name__ = name
        self.__qualname__ = f"{am.name}.{name}"

    def __metta__(self) -> Atom:
        """An async bound function in term position mentions as its head symbol."""
        return Symbol(self._name)

    async def __call__(self, *args: Any) -> Any:
        return await self.one(*args)

    async def one(self, *args: Any) -> Any:
        name = self._name
        return await self._am.call(lambda m: m.fn[name](*args).one())

    async def first(self, *args: Any) -> Any:
        name = self._name
        return await self._am.call(lambda m: m.fn[name](*args).first())

    async def all(self, *args: Any) -> list:
        name = self._name
        return await self._am.call(lambda m: list(m.fn[name](*args)))

    def __repr__(self) -> str:
        return f"<async engine function {self._name} on {self._am.name}>"


class _AsyncCompositeEngineFunction:
    """Async callable for a word represented by a composite term recipe."""

    def __init__(self, am: AsyncMeTTa, recipe: OperatorRecipe) -> None:
        self._am = am
        self._recipe = recipe
        self.__name__ = recipe.word
        self.__qualname__ = f"{am.name}.{recipe.word}"

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return await self.one(*args, **kwargs)

    async def one(self, *args: Any, **kwargs: Any) -> Any:
        recipe = self._recipe
        return await self._am.call(lambda m: m.answers(recipe(*args, **kwargs)).one())

    async def first(self, *args: Any, **kwargs: Any) -> Any:
        recipe = self._recipe
        return await self._am.call(lambda m: m.answers(recipe(*args, **kwargs)).first())

    async def all(self, *args: Any, **kwargs: Any) -> list:
        recipe = self._recipe
        return await self._am.call(lambda m: list(m.answers(recipe(*args, **kwargs))))

    def __repr__(self) -> str:
        return f"<async composite engine function {self._recipe.word} on {self._am.name}>"


async def connect(
    space: str | Symbol | Expression | Space = _DEFAULT_SPACE,
    *,
    metta: Space | None = None,
) -> AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return await AsyncMeTTa(space, metta=metta).start()
