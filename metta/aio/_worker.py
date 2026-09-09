"""Purpose: the same engine without blocking an event loop. AsyncMeTTa
proxies a MeTTa space onto one dedicated worker thread that holds an
attached Prolog engine, the aiosqlite architecture (one thread per
connection, a request queue, results delivered back through the loop), so
awaiting a long query lets every other coroutine keep running. Requests on
one worker are serialized; separate workers share the runtime through private
engines. interrupt() stops the running
evaluation through the engine's own thread_signal, the sqlite3 reading,
and a cancelled task fires it on its own call, so asyncio timeouts stop
the engine instead of abandoning it.
Guarantees:
  - scope-owned workers and requests use lib_thread's cleanup and completion
    rows; exit joins abandoned foreign calls before releasing their inputs
    [tested: test_scope_owns_an_async_worker_and_its_requests,
    test_scope_joins_a_cancelled_request_on_a_borrowed_async_worker;
    commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
  - subscription acquisition publishes on the worker, so synchronous scope
    cleanup does not wait for an event-loop continuation and closes waiting
    consumers [tested:
    test_async_subscription_stop_needs_only_the_workers_acquisition_receipt,
    test_scope_closes_an_async_subscription_on_a_borrowed_worker;
    commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
  - Prolog-backed definitions require their reference function and construct
    and apply the synchronous decorator on the owning worker
    [tested: test_async_prolog_define_requires_the_reference_function,
    test_async_prolog_define_registers_and_applies_on_its_worker; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
  - AsyncMeTTa.space delegates construction to MeTTa.space and preserves the
    caller creation site and borrowed provider lifecycle [tested:
    test_a_journaled_async_space_round_trips_a_fact,
    test_async_space_provider_backing_attaches_and_remains_borrowed,
    test_async_anonymous_space_repr_keeps_the_submitting_site; commit=d263b1f05e3ca3a0621122c1fc60d295b87692b0]
  - that delegation carries the journal's one-open schema rename, so the
    migration is not a synchronous-only spelling [tested:
    test_the_async_space_factory_exposes_replay_rename; commit=694dff934a11dbc2ee99267b60f39564053baf87]
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
    test_aio_the_close_sentinel_survives_a_full_queue; commit=cd8a597152395767587bbc64b6034400c81dd7b3]
  - an acquired subscription belongs to its AsyncMeTTa until it closes, and a
    callback whose event loop has closed retires itself before another write
    can reach it [tested:
    test_aio_subscription_retires_when_its_event_loop_closes,
    test_aio_close_cancels_every_acquired_subscription;
    commit=4a52d2d77621b917f20b0c5618ea87de07cbbb71]
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
  - async declaration methods reuse the catalog-generated policy aliases and
    own no duplicate Literal lists [tested: tests/checks/check_policy_inventory.py;
    commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
  - all fifteen synchronous declaration heads have asynchronous mirrors,
    including ``reacts`` for ``(on ...)`` and ``consumption`` for
    ``(source ...)``, while ``reaction`` remains and no ``declare_*``
    aliases return [tested:
    test_aio_covers_the_whole_synchronous_surface,
    test_m7_narrow_core_surface; commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
  - source() mirrors the synchronous round-trippable text view on the owning
    worker [tested: test_aio_declare_and_register_delegations_land;
    commit=42502e9d4a7fedd419856d5e6a1c291fc18ba644]
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
  - async derivation keeps the synchronous effect contract: premises execute,
    while an explicit speculative scope discards engine writes [tested:
    test_derivation_effects_are_explicit_and_speculation_discards_engine_writes;
    commit=418bed011dfc47bb2c2d9e6b51e0d2a6f7b7e729]
  - reader-token registration and removal run on the owning engine worker and
    mirror the synchronous surface [tested:
    test_aio_plain_methods_forward_on_the_worker and
    test_async_anonymous_space_repr_keeps_the_submitting_site;
    commit=50d1de4d0ead4a0c3997f9b2ef58631bbafaede3]
  - eval carries every synchronous option, with lazy pulls and releases kept
    on the worker and unfinished selections owned by the connection [tested:
    test_async_evaluation_options_reach_the_same_engine_choices,
    test_async_evaluation_cleanup_is_owned_and_retryable; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - one stop signal per active request preserves error translation; pending
    writes lose to close while child releases remain admitted, and closing a
    borrower leaves another connection's work running [tested:
    test_async_evaluation_repeated_stops_share_one_transition_signal,
    test_async_evaluation_parent_cleanup_rejects_an_already_queued_write,
    test_async_evaluation_borrower_cleanup_leaves_the_other_connection_running;
    commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - direct, saga, and reified-world evaluations expose Undefined in their
    return types wherever Well Founded Semantics can return it [tested:
    test_async_result_hints_preserve_undefined_answers; commit=71f43dd54034363d3bf8b2d1a3189a63b9e4ce1a]
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
    and sample mirrors the synchronous random.choices-shaped method [tested:
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
import contextlib
import contextvars
import functools
import logging
import math
import os
import queue
import threading
import warnings
import weakref
from collections import abc as _abc
from collections.abc import Callable, Coroutine, Iterable, Mapping
from typing import Any, Literal, Self, overload

import metta._spaces.lifetime as _scope
from metta._atoms.designation import _DEFAULT_SPACE, _UNSET, _SpaceId
from metta._atoms.factories import Atom, Expression, Symbol, Undefined
from metta._binding.runtime import Runtime, bridge, runtime
from metta._errors.errors import Interrupted, MettaError
from metta._faces.space import Space
from metta._spaces.cursor import require_deadline
from metta._spaces.handle import _creation_site
from metta._spaces.scope import selected as _selected_under
from metta.aio import DEFAULT_CLOSE_TIMEOUT
from metta.doors import EvaluationAnswer
from metta.vocabularies import (
    ArgumentDelivery,
    Determinism,
    EffectClass,
    ImageMode,
    JournalSync,
    OnError,
    SubscriptionEdge,
)

logger = logging.getLogger(__name__)


_LIVE_WORKERS: weakref.WeakSet[_EngineThread] = weakref.WeakSet()
_LIVE_WORKERS_LOCK = threading.Lock()


def _set_future_exception(future: asyncio.Future[None], failure: BaseException) -> None:
    if not future.done():
        future.set_exception(failure)


def _set_future_result(future: asyncio.Future[None]) -> None:
    if not future.done():
        future.set_result(None)


class _Request:
    __slots__ = (
        "abandoned", "context", "during_close", "fn", "future", "interrupted",
        "loop", "owner", "scope", "target", "worker",
    )

    def __init__(self, fn, owner, loop, future, worker, *, during_close=False) -> None:
        self.fn = fn
        self.owner = weakref.ref(owner)
        self.target = owner._m
        self.worker = worker
        self.during_close = during_close
        self.interrupted = False
        self.loop = loop
        self.future = future
        self.abandoned = threading.Event()
        # The submitting task's contextvars, so scoped state (limits(),
        # an open batch) crosses to the worker thread with the request,
        # which is what makes the with-blocks async-correct THROUGH the
        # thread hop and not only beside it.
        self.context = contextvars.copy_context()
        self.scope = _scope.own("future", self.cancel)

    def cancel(self, scope: str | None = None) -> None:
        """Abandon queued work or signal this exact running request."""
        self.abandoned.set()
        if scope is not None:
            # A scope can cancel from its timer thread. A closed loop has no
            # waiter to wake; the worker still publishes its completion receipt.
            with contextlib.suppress(RuntimeError):
                self.loop.call_soon_threadsafe(
                    _set_future_exception, self.future, _scope.Cancelled(scope)
                )
        self.worker.interrupt_if_running(self)


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
                        _scope.finished(request.scope)
                        continue  # cancelled while queued: never runs
                    with self._transition:
                        with self._state_lock:
                            closing = self._state == "closing"
                        # A close with child resources keeps the worker alive
                        # for their releases. Accepted ordinary work still
                        # loses to close before it starts, as an executor's
                        # set_running_or_notify_cancel checks at dispatch:
                        # https://github.com/python/cpython/blob/v3.14.4/Lib/concurrent/futures/thread.py
                        owner = request.owner()
                        if owner is None:
                            closing = True
                        else:
                            with owner._subscriptions_lock:
                                closing |= not request.during_close and (owner._closing or owner._closed)
                        del owner
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

    def interrupt_if_running(self, request: _Request | None, *, owner: AsyncMeTTaBase | None = None) -> bool:
        """Signal the engine thread if `request` is the one running now,
        or if anything is running when request is None. Answers whether a
        signal was sent. Repeated stops of one request coalesce until its
        transition drain completes; a second signal could interrupt the
        first refusal's own engine-backed error translation.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        with self._state_lock:
            swi_thread = self._swi_thread
        with self._transition:
            current = self._current
            if current is None or (request is not None and current is not request):
                return False
            if current.interrupted or (owner is not None and current.owner() is not owner):
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
            current.interrupted = True
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

    def stop(self, timeout: float | None = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronously stop this worker and detach its Prolog engine."""
        if timeout is not None:
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


def _raise_lifecycle_failures(message: str, failures: list[BaseException]) -> None:
    """Preserve one cleanup failure; group several in attempted order."""
    if len(failures) == 1:
        raise failures[0]
    if failures:
        raise BaseExceptionGroup(message, failures)


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
    finally:
        _scope.finished(
            request.scope, payload if failed and not request.abandoned.is_set() else None
        )



# views and evaluation import worker state during initialization
from metta.aio import _views  # noqa: E402


class AsyncMeTTaBase:
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

    def __init__(
        self,
        space: str | Symbol | Expression | Space = _DEFAULT_SPACE,
        *,
        metta: Space | None = None,
    ) -> None:
        self._m = metta if metta is not None else Space(space)
        self._worker = _EngineThread()
        self._closed = False
        self._closing = False
        self._owner = True
        self._subscriptions: set[Any] = set()
        self._subscriptions_lock = threading.RLock()
        _scope.own("cleanup", functools.partial(self.stop, timeout=None))

    @classmethod
    def _sharing(cls, metta: Space, worker: _EngineThread) -> Self:
        shared = cls.__new__(cls)
        shared._m = metta
        shared._worker = worker
        shared._closed = False
        shared._closing = False
        shared._owner = False
        shared._subscriptions = set()
        shared._subscriptions_lock = threading.RLock()
        return shared

    def _require_open_locked(self) -> None:
        if self._closed or self._closing:
            state = "closed" if self._closed else "closing"
            msg = f"this AsyncMeTTa is {state}"
            raise MettaError(msg)

    def _track_subscription(self, stream: _views._AsyncSubscription | _aio__evaluation._EvaluationGroup) -> None:
        """Make an acquired stream part of this connection's close scope."""
        with self._subscriptions_lock:
            self._require_open_locked()
            self._subscriptions.add(stream)

    def _forget_subscription(self, stream: _views._AsyncSubscription | _aio__evaluation._EvaluationGroup) -> None:
        with self._subscriptions_lock:
            self._subscriptions.discard(stream)

    def _begin_close(self) -> tuple[_views._AsyncSubscription | _aio__evaluation._EvaluationGroup, ...]:
        with self._subscriptions_lock:
            if self._closing:
                msg = "this AsyncMeTTa is already closing"
                raise MettaError(msg)
            self._closing = True
            return tuple(self._subscriptions)

    def _abort_close(self) -> None:
        with self._subscriptions_lock:
            self._closing = False

    def _finish_close(self) -> None:
        with self._subscriptions_lock:
            self._closed = True
            self._closing = False

    @property
    def name(self) -> _SpaceId:
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
        with self._subscriptions_lock:
            self._require_open_locked()
        await self._worker.start()
        return self

    async def _submit(self, fn: Callable[[Space], Any], *, during_close: bool) -> Any:
        await self._worker.start()
        loop = asyncio.get_running_loop()
        request = _Request(fn, self, loop, loop.create_future(), self._worker, during_close=during_close)
        try:
            if during_close:
                self._worker.submit(request)
            else:
                # Publication of a request and publication of close are ordered.
                # A request already accepted is rejected or interrupted by the
                # worker close; one that lost this race never enters the queue.
                with self._subscriptions_lock:
                    self._require_open_locked()
                    self._worker.submit(request)
        except BaseException:
            _scope.finished(request.scope)
            raise
        try:
            return await request.future
        except asyncio.CancelledError:
            # The listener is gone; stop the engine working for it. A
            # request still queued is skipped, a running one is signalled.
            request.cancel()
            raise

    async def _resource_call(self, fn: Callable[[Space], Any]) -> Any:
        """Release an acquired child while its parent is closing."""
        with _scope.suspend():
            return await self._submit(fn, during_close=True)

    async def _subscription_call(self, fn: Callable[[Space], Any]) -> Any:
        """Use the public crossing unless parent close already claimed it."""
        with self._subscriptions_lock:
            closing = self._closing
        with _scope.suspend():
            if closing:
                return await self._resource_call(fn)
            return await self.call(fn)

    async def call[T](self, fn: Callable[[Space], T]) -> T:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        with self._subscriptions_lock:
            self._require_open_locked()
        return await self._submit(fn, during_close=False)

    def interrupt(self) -> bool:
        """Stop the evaluation the worker is running right now; answers
        whether anything was running (idle is a no-op, sqlite3's own
        reading). The stopped call raises metta.Interrupted; whatever it
        completed before the stop, writes included, stands. Callable from
        any thread or task.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._worker.interrupt_if_running(None)

    # ----------------------------------- methods the worker needs its own body for

    async def count(self) -> int:
        """Return the number of atoms in this space."""
        return await self.call(len)

    @overload
    async def eval(
        self,
        target: Any,
        /,
        *more: Any,
        timeout: float | None=None,
        inferences: int | None=None,
        under: Any=_UNSET,
        theory: Any | None=None,
        interpreter: Any | None=None,
        answer: EvaluationAnswer | str = "all",
        delivery: ArgumentDelivery | str,
        limit: int | None = None,
        image: ImageMode | str | None = None,
        on_error: OnError | str = "keep",
        determinism: Determinism | str = "nondet",
        **values: Any,
    ) -> Any: ...

    @overload
    async def eval(
        self,
        target: Any,
        /,
        *more: Any,
        timeout: float | None=None,
        inferences: int | None=None,
        under: Any=_UNSET,
        theory: Any | None=None,
        interpreter: Any | None=None,
        answer: EvaluationAnswer | str,
        delivery: ArgumentDelivery | str = "atoms",
        limit: int | None = None,
        image: ImageMode | str | None = None,
        on_error: OnError | str = "keep",
        determinism: Determinism | str = "nondet",
        **values: Any,
    ) -> Any: ...

    @overload
    async def eval(
        self,
        target: Any,
        /,
        *,
        timeout: float | None=...,
        inferences: int | None=...,
        under: Any=...,
        theory: Any | None=...,
        interpreter: Any | None=...,
        **values: Any,
    ) -> list[Atom | Undefined]: ...

    @overload
    async def eval(
        self,
        target: Any,
        _second: Any,
        /,
        *more: Any,
        timeout: float | None=...,
        inferences: int | None=...,
        under: Any=...,
        theory: Any | None=...,
        interpreter: Any | None=...,
        **values: Any,
    ) -> list[list[Atom | Undefined]]: ...

    async def eval(
        self,
        target: Any,
        /,
        *more: Any,
        timeout: float | None=None,
        inferences: int | None=None,
        under: Any=_UNSET,
        theory: Any | None=None,
        interpreter: Any | None=None,
        answer: EvaluationAnswer | str = "all",
        delivery: ArgumentDelivery | str = "atoms",
        limit: int | None = None,
        image: ImageMode | str | None = None,
        on_error: OnError | str = "keep",
        determinism: Determinism | str = "nondet",
        **values: Any,
    ) -> Any:
        """Evaluate on the worker with the synchronous door's option product.

        Eager and scalar choices return their values after one awaited request.
        The answers choice returns a replayable asynchronous view; stream
        returns a single-pass asynchronous view. Pull and close stay on this
        worker, and the parent owns any unfinished selection. Use async with
        on a returned view when stopping iteration early.

        Holes, bindings, algebra, theory, interpreter, delivery, images, bounds,
        error-answer policy and cardinality keep their synchronous meanings.
        """
        carrier = _selected_under(under)

        def evaluate(space: Space) -> Any:
            return space.eval(
                target, *more, timeout=timeout, inferences=inferences,
                under=carrier if carrier is not None else _UNSET,
                theory=theory, interpreter=interpreter,
                answer=answer, delivery=delivery, limit=limit, image=image,
                on_error=on_error, determinism=determinism, **values,
            )

        if answer in (EvaluationAnswer.answers, EvaluationAnswer.stream):
            # views and evaluation import worker state during initialization
            from metta.aio._evaluation import _EvaluationGroup  # noqa: PLC0415

            return await _EvaluationGroup(self).open(evaluate, batch=bool(more))
        return await self.call(evaluate)

    async def copy(self) -> Self:
        """This space's contents in a new anonymous space; Space.copy,
        the clone borrowing this connection's worker.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        clone = await self.call(lambda m: m.copy())
        return type(self)._sharing(clone, self._worker)

    async def reify(self) -> _views.AsyncWorld:
        """Capture one immutable world on the owning engine worker."""
        world = await self.call(lambda m: m.reify())
        return _views.AsyncWorld(self, world)

    async def commit(self, world: _views.AsyncWorld) -> None:
        """Commit an async world through the worker that produced it."""
        if not isinstance(world, _views.AsyncWorld):
            msg = f"commit expects an AsyncWorld, got {type(world).__name__}"
            raise TypeError(msg)
        if world._am._worker is not self._worker:
            msg = "an async world must be committed through its originating engine worker"
            raise MettaError(msg)
        await self.call(lambda m: m.commit(world._world))

    def saga(self, receipts: AsyncMeTTaBase) -> _views.AsyncSaga:
        """Open an async saga whose complete scopes run on this worker."""
        if not isinstance(receipts, AsyncMeTTaBase):
            msg = (
                "async saga receipts must be an AsyncMeTTa, got "
                f"{type(receipts).__name__}"
            )
            raise TypeError(msg)
        if receipts._worker is not self._worker:
            msg = "an async saga and its receipt space must share one engine worker"
            raise MettaError(msg)
        return _views.AsyncSaga(self, receipts)

    async def space(
        self,
        name: str | Symbol | Expression | Space | None = None,
        backing: Any = None,
        *,
        inherits: AsyncMeTTaBase | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        journal: str | os.PathLike[str] | None = None,
        schema: _abc.Mapping[str, Any] | None = None,
        sync: JournalSync = JournalSync.none,
        rename: _abc.Mapping[str, str] | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> Self:
        """Create or open a space through MeTTa.space on this connection's worker.

        Native, provider, remote, and journaled construction use the synchronous
        context door, including a journal's one-open ``rename`` migration.
        Returned spaces borrow the connection's worker, so closing one does not
        stop the connection. Anonymous handles record the submitting coroutine's
        creation site.
        """
        if inherits is not None and inherits._worker is not self._worker:
            msg = "an inherited async space must share this engine worker"
            raise ValueError(msg)
        parent = None if inherits is None else inherits._m
        requested_grants = tuple(grants)
        site = _creation_site() if _created_at is None else _created_at
        handle = await self.call(
            lambda m: m.metta.space(
                name, backing, inherits=parent, restricted=restricted, grants=requested_grants,
                journal=journal, schema=schema, sync=sync, rename=rename, _created_at=site,
            )
        )
        return type(self)._sharing(handle, self._worker)

    async def op(
        self,
        fn: Callable,
        /,
        *,
        effect: EffectClass | str,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=extensions/python/metta/_declare/operations.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Callable:
        """Register a callable through the short operation form."""
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

    async def rules(self, fn: Callable) -> Any:
        """Collect and land a non-exclusive equation bundle on the worker.

        An awaitable CALL rather than a decorator, which is the same answer
        define() gives to the same problem: decoration cannot await, so this
        method accepts only the applied form. It was
        excluded from the async surface for the first reading of that, which
        left an async caller unable to land a bundle at all
        [measured 2026-08-31].
        """
        return await self.call(lambda space: space.rules(fn))

    async def pre_add(self, fn: Callable) -> Any:
        """Compile or accept one unary judge and claim this space's write hook.

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
        returned handle's own calls are synchronous methods; evaluate
        through fn(name) or run() from async code.

        The reference function is required, including with prolog=. The
        synchronous decorator is constructed and applied on the owning worker.

        `name=` preserves an exact spelling on the async surface. Without it,
        an async caller installing `prime?` or an authored underscore had no
        equivalent of the synchronous define method [measured 2026-08-31].
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if fn is None:
            msg = (
                "AsyncMeTTa.define needs the reference function; pass "
                "await am.define(function, prolog=source). A synchronous "
                "decorator would register on the caller's thread after the "
                "owning worker may have closed"
            )
            raise TypeError(msg)
        if prolog is None:
            return await self.call(
                lambda m: m.define(
                    fn, name=name, accessors=accessors, methods=methods
                )
            )
        # Construct and apply the synchronous decorator in one worker request.
        return await self.call(lambda m: m.define(prolog=prolog, name=name)(fn))

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
        """Make each awaited CALL in the block one engine transaction.

        The write doors included: the request carries the submitting task's
        contextvars to the worker, so the thread hop is not a hole in the
        scope.
        """
        return self._m.atomic()

    def speculative(self):
        """Answer awaited CALLS while discarding their engine writes.

        The write doors included: `await am.add(atom)` inside the block
        leaves nothing behind
        [tested: test_an_async_write_door_inherits_the_scope_across_the_worker].
        """
        return self._m.speculative()

    def batch(self) -> _views._AsyncBatch:
        """Collect this space's add() calls and cross once at exit,
        the synchronous batch's async twin: `async with am.batch():`.
        The same stated edges apply: reads see the pre-batch space,
        remove and clear refuse, an exception discards.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _views._AsyncBatch(self)

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

    def stats(self) -> _views._AsyncStats:
        """The engine's counters over an async with-block, as deltas.

        async with am.stats() as s:
            await am.match(...)
        s.inferences
        """
        return _views._AsyncStats(self)

    def assuming(self, *facts: Any) -> _views._AsyncAssuming:
        """Facts held only inside an async with-block: added on entry,
        removed on exit, exceptions included.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _views._AsyncAssuming(self, facts)

    async def prepare(self, *patterns: Any, where: Any | None = None) -> _views._AsyncPrepared:
        """A prepared query whose solve() is awaitable; the shape builds
        once on the worker, columns readable without a round trip.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        prepared = await self.call(lambda m: m.prepare(*patterns, where=where))
        return _views._AsyncPrepared(self, prepared)

    def stream(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        under: Any = _UNSET,
    ) -> _views._AsyncCursor:
        """match(), pulled asynchronously: one row per worker round trip.

            async with am.stream(S.edge(V.a, V.b)) as rows:
                async for row in rows:
                    ...

        Iterating without the async-with also works; aclose() is then the
        caller's duty, the finalization reading the data model gives
        asynchronous iterators.
        """
        return _views._AsyncCursor(
            self, patterns, where, timeout, inferences, limit=limit, under=under
        )

    def subscribe(
        self,
        pattern: Any,
        *,
        on: SubscriptionEdge = SubscriptionEdge.add,
        where: Any | None = None,
        queue_max: int | None = None,
    ) -> _views._AsyncSubscription:
        """A standing query as an async event stream: every matching
        write becomes an Event on an asyncio queue, consumed with
        async-for. The synchronous surface's callback form stays there;
        here the stream IS the delivery.

            async with am.subscribe(S.order(V.id), on="add") as events:
                async for event in events:
                    ...
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _views._AsyncSubscription(self, pattern, on, queue_max, where=where)

    def watch(
        self,
        pattern: Any,
        *,
        on: SubscriptionEdge = SubscriptionEdge.add,
        where: Any | None = None,
        deadline: float | None = None,
        queue_max: int | None = None,
    ) -> _views._AsyncSubscription:
        """Observe matching writes, raising Timeout after each quiet deadline.

        This method once shared subscribe()'s signature and body despite being
        named watch(), so an async caller had no way to set the quiet deadline
        that peek() and take() both provide
        [measured 2026-08-31].
        """
        require_deadline(deadline)
        return _views._AsyncSubscription(
            self, pattern, on, queue_max, deadline=deadline, where=where
        )

    @property
    def fn(self) -> _views._AsyncFunctionNamespace:
        """Engine functions as async callables, by attribute or exact name.

        ``m.fn.car_atom`` transliterates underscores to hyphens and
        ``m.fn["=="]`` preserves exact punctuation, the same two forms the
        sync namespace has. Resolution is lazy: the worker is asked when the
        function is awaited, so an unknown name raises there rather than at
        access.
        """
        return _views._AsyncFunctionNamespace(self)


    # -------------------------------------------------------------- lifecycle

    async def _release_subscriptions(
        self, subscriptions: tuple[_views._AsyncSubscription | _aio__evaluation._EvaluationGroup, ...]
    ) -> None:
        """Release every acquired stream before reporting any failure."""
        failures: list[BaseException] = []
        for subscription in subscriptions:
            try:
                await subscription._release()
            except BaseException as exc:  # noqa: BLE001 -- every sibling releases before a failure leaves
                failures.append(exc)
        msg = "closing AsyncMeTTa subscriptions failed"
        _raise_lifecycle_failures(msg, failures)

    def _stop_subscriptions(
        self, subscriptions: tuple[_views._AsyncSubscription | _aio__evaluation._EvaluationGroup, ...]
    ) -> None:
        """Synchronous counterpart used when no event loop is running."""
        failures: list[BaseException] = []
        for subscription in subscriptions:
            try:
                subscription._stop()
            except BaseException as exc:  # noqa: BLE001 -- every sibling releases before a failure leaves
                failures.append(exc)
        msg = "stopping AsyncMeTTa subscriptions failed"
        _raise_lifecycle_failures(msg, failures)

    async def aclose(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Cancel acquired streams, then stop and detach the worker."""
        timeout = _close_timeout(timeout)
        subscriptions = self._begin_close()
        try:
            if subscriptions:
                self._worker.interrupt_if_running(None, owner=None if self._owner else self)
            await _shielded(self._release_subscriptions(subscriptions))
        except BaseException:
            # A child that failed to cancel remains tracked, and the live
            # worker makes an explicit retry possible.
            self._abort_close()
            raise
        self._finish_close()
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

    def stop(self, timeout: float | None = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronously cancel streams and stop; None waits until the worker exits."""
        if timeout is not None:
            timeout = _close_timeout(timeout)
        subscriptions = self._begin_close()
        try:
            if subscriptions:
                self._worker.interrupt_if_running(None, owner=None if self._owner else self)
            self._stop_subscriptions(subscriptions)
        except BaseException:
            self._abort_close()
            raise
        self._finish_close()
        if self._owner:
            self._worker.stop(timeout)

    async def __aenter__(self) -> Self:
        return await self.start()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def __del__(self) -> None:
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

    def __repr__(self) -> str:
        state = "closed" if self._closed else self._worker.state
        return f"AsyncMeTTa({self._m!r}, {state})"

# Resolve annotations after definitions so peer imports can finish.
import metta.aio._evaluation as _aio__evaluation  # noqa: E402 -- deferred annotation bindings
