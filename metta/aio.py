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
    test_async_evaluation_cleanup_is_owned_and_retryable; commit=WORKTREE]
  - one stop signal per active request preserves error translation; pending
    writes lose to close while child releases remain admitted, and closing a
    borrower leaves another connection's work running [tested:
    test_async_evaluation_repeated_stops_share_one_transition_signal,
    test_async_evaluation_parent_cleanup_rejects_an_already_queued_write,
    test_async_evaluation_borrower_cleanup_leaves_the_other_connection_running;
    commit=WORKTREE]
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
from collections import abc as _abc
from collections.abc import Callable, Coroutine, Iterable, Mapping
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, Literal, Self, TypeVar, overload

from . import ops as _ops_module
from ._api_types import _DEFAULT_SPACE, _SpaceId
from ._engine import Runtime, bridge, runtime
from ._name_mapping import OperatorRecipe, operator_attribute_target
from ._space import Space, _creation_site
from ._space_objects import EngineProfile, Explanation, FunctionCost, require_deadline
from ._under import _UNSET
from ._under import selected as _selected_under
from .atoms import Atom, Expression, Symbol, Undefined
from .doors import EvaluationAnswer
from .errors import Interrupted, MettaError, Timeout
from .results import Rows
from .subscribe import _capacity
from .vocabularies import (
    AgendaPolicy,
    AnswerPolicy,
    ArgumentDelivery,
    Atomicity,
    Delivery,
    Determinism,
    EffectClass,
    EventOrder,
    Fidelity,
    ImageMode,
    JournalSync,
    OnError,
    SaveFormat,
    SemiringOrder,
    SourceKind,
    SubscriptionEdge,
    World,
)

if TYPE_CHECKING:
    # Named only by mirrored return annotations, which `from __future__ import
    # annotations` keeps as text. Space reaches both through _satellite(), so
    # importing them here at runtime would make `import metta.aio` pay for
    # surfaces the caller may never touch.
    from ._aio_evaluation import _EvaluationGroup
    from ._api_types import TemplateLike
    from ._debug import Debugger
    from ._recording import Recording
    from ._trace import Trace
    from .lint import Finding

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
    __slots__ = ("abandoned", "context", "during_close", "fn", "future", "interrupted", "loop", "owner", "target")

    def __init__(self, fn, owner, loop, future, *, during_close=False) -> None:
        self.fn = fn
        self.owner = weakref.ref(owner)
        self.target = owner._m
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

    def interrupt_if_running(self, request: _Request | None, *, owner: AsyncMeTTa | None = None) -> bool:
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
        self._closing = False
        self._owner = True
        self._subscriptions: set[Any] = set()
        self._subscriptions_lock = threading.RLock()

    @classmethod
    def _sharing(cls, metta: Space, worker: _EngineThread) -> AsyncMeTTa:
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

    def _track_subscription(self, stream: _AsyncSubscription | _EvaluationGroup) -> None:
        """Make an acquired stream part of this connection's close scope."""
        with self._subscriptions_lock:
            self._require_open_locked()
            self._subscriptions.add(stream)

    def _forget_subscription(self, stream: _AsyncSubscription | _EvaluationGroup) -> None:
        with self._subscriptions_lock:
            self._subscriptions.discard(stream)

    def _begin_close(self) -> tuple[_AsyncSubscription | _EvaluationGroup, ...]:
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
        with self._subscriptions_lock:
            self._require_open_locked()
        await self._worker.start()
        return self

    async def _submit(self, fn: Callable[[Space], Any], *, during_close: bool) -> Any:
        await self._worker.start()
        loop = asyncio.get_running_loop()
        request = _Request(fn, self, loop, loop.create_future(), during_close=during_close)
        if during_close:
            self._worker.submit(request)
        else:
            # Publication of a request and publication of close are ordered.
            # A request already accepted is rejected or interrupted by the
            # worker close; one that lost this race never enters the queue.
            with self._subscriptions_lock:
                self._require_open_locked()
                self._worker.submit(request)
        try:
            return await request.future
        except asyncio.CancelledError:
            # The listener is gone; stop the engine working for it. A
            # request still queued is skipped, a running one is signalled.
            request.abandoned.set()
            self._worker.interrupt_if_running(request)
            raise

    async def _resource_call(self, fn: Callable[[Space], Any]) -> Any:
        """Release an acquired child while its parent is closing."""
        return await self._submit(fn, during_close=True)

    async def _subscription_call(self, fn: Callable[[Space], Any]) -> Any:
        """Use the public crossing unless parent close already claimed it."""
        with self._subscriptions_lock:
            closing = self._closing
        if closing:
            return await self._resource_call(fn)
        return await self.call(fn)

    async def call(self, fn: Callable[[Space], Any]) -> Any:
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
            from ._aio_evaluation import (  # noqa: PLC0415 -- lazy worker-owned results depend on this module
                _EvaluationGroup,
            )

            return await _EvaluationGroup(self).open(evaluate, batch=bool(more))
        return await self.call(evaluate)

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

    async def space(
        self,
        name: str | Symbol | Expression | Space | None = None,
        backing: Any = None,
        *,
        inherits: AsyncMeTTa | None = None,
        restricted: bool = False,
        grants: _abc.Iterable[str] = (),
        journal: str | os.PathLike[str] | None = None,
        schema: _abc.Mapping[str, Any] | None = None,
        sync: JournalSync = JournalSync.none,
        rename: _abc.Mapping[str, str] | None = None,
        _created_at: tuple[str, int] | None = None,
    ) -> AsyncMeTTa:
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
        return AsyncMeTTa._sharing(handle, self._worker)

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
        on: SubscriptionEdge = SubscriptionEdge.add,
        where: Any | None = None,
        queue_max: int | None = None,
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
        on: SubscriptionEdge = SubscriptionEdge.add,
        where: Any | None = None,
        deadline: float | None = None,
        queue_max: int | None = None,
    ) -> _AsyncSubscription:
        """Observe matching writes, raising Timeout after each quiet deadline.

        This method once shared subscribe()'s signature and body despite being
        named watch(), so an async caller had no way to set the quiet deadline
        that peek() and take() both provide
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
        ``m.fn["=="]`` preserves exact punctuation, the same two forms the
        sync namespace has. Resolution is lazy: the worker is asked when the
        function is awaited, so an unknown name raises there rather than at
        access.
        """
        return _AsyncFunctionNamespace(self)

    # ---------------------------------------------- generated mirror
    # Generated by tools/doorgen.py through its aiogen backend, from metta.doors.
    # Each method preserves its row's signature and documentation in one worker
    # round trip. Change the row and its implementation, then regenerate.
    # Handwritten worker methods stay above this region and pass row parity;
    # async_signature and async_reason declare an intentional difference.

    async def space_names(self) -> list[str]:
        """Every space name this engine registers, sorted: '&self' and
        '&metta' from boot, every native space something created or wrote to,
        and every foreign space currently bound. (new-space) and (spawn ...)
        create, so their answers are here at once; naming a space never
        registers it, so Space('&kb') is not here until a write, and a bind!
        token's target appears once something is stored under it.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.space_names())

    async def drop(self) -> None:
        """Clear this space and release an anonymous name for reuse.

        Dropping retires every space-owned catalog declaration, including
        algebra rows and their Python mirrors.
        Dropping unregisters a Python provider and closes only backing state
        owned by this handle. A foreign provider with a clear/drop lifecycle,
        such as MORK, releases its provider state.
        A named space's public name is not an anonymous allocation and never
        enters the anonymous pool. The engine-owned &self and &metta roots
        refuse before any Python-side state changes; drop the caller's own
        context or a named space instead.
        Subscriptions on the space cancel with it: a pooled name reused later
        must not deliver to the old life's watchers. The handle itself dies
        here, and dropping twice is a no-op, as closing twice is.

        Engine teardown must succeed before Python cleanup is discarded.
        If later cleanup fails, call drop() again to finish it. The handle
        refuses other operations in that state and retains its anonymous name
        until cleanup succeeds; retrying does not repeat engine teardown.
        """
        return await self.call(lambda m: m.drop())

    async def run(
        self,
        source: str | TemplateLike,
        /,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
        **values: Any,
    ) -> list[list[Atom]]:
        """Run MeTTa source: one list of answers per ! directive.

        The pipeline is the engine's own reader, compiler and evaluator, so
        the answers are exactly what the CLI would print, kept grouped per
        directive instead of flattened. Equations and facts in the source
        land in this space.

        The source may carry HOLES, which are bindings by position:

            m.run(t"!(fib {n})")            # a 3.14 t-string literal
            m.run("!(fib {n})", n=10)       # the same on every version

        Each hole is spliced into the text as a generated symbol and bound to
        its value, so a str stays one String atom and never has to be escaped.
        Values enter through `encode`: an int is a Number, a str a String, an
        Atom itself, a Space its handle. The markers at a hole are the atom
        constructors, `{Symbol(name)}`, `{Grounded(obj)}` and `{parse(text)}`,
        with the specs `:sym`, `:py` and `:expr` as their short forms; `!r`
        and `!s` convert in Python first and enter the result as text. A hole
        inside a string literal, a comment or a symbol is refused with its
        line and column.

        `bind()` is the same substitution by NAME, for a value several calls
        share, the way DuckDB reads a local dataframe by its variable name:

            with m.bind({"graph": my_graph}):
                m.run("!(py-len graph)")

        Each named symbol substitutes to its value (objects by identity),
        after reading, before anything runs. It is a BLOCK rather than a
        keyword because a binding mapping is the kind of value that grows,
        and a block grows down the page where a keyword has to fit beside
        everything else on the call. Every call that accepts a target reads the
        same scope, so one block covers run(), eval(), and answers() together.
        A binding names a symbol and so replaces EVERY occurrence of it,
        including one the author meant as a symbol; a hole is positional and
        cannot reach anything but itself.

        `timeout` (seconds) and `inferences` (engine steps) bound the call
        with the engine's own guards; passing either raises TimeLimitError
        or InferenceLimitError when the bound is hit, and whatever the
        source completed before the stop, writes included, stands.

        `with m.capture() as output` collects printed text in `output.text`
        without changing this method's return shape. `with m.atomic()`
        and `with m.speculative()` scope execution policy without boolean
        combinations on each call. Atomic commits or rolls
        back each complete source; speculative answers and discards its
        writes. Both cover engine state; Python side effects and subscription
        callbacks already fired stay where they happened.

        A term the engine hands back unevaluated is an ordinary MeTTa value,
        not a failure: `!(hello world)` answers `(hello world)` and that is
        the whole of hello world in this language. eval_status() reports
        which answers reduced and which did not, as data, for a caller who
        wants to decide about it.
        """
        return await self.call(
            lambda m: m.run(source, timeout=timeout, inferences=inferences, **values)
        )

    async def explain(
        self,
        query: Any,
        /,
        *,
        analyze: bool=False,
        allow_writes: bool=False,
        **values: Any,
    ) -> Explanation:
        """What the engine will do with this query, reflected rather than run.

            e = m.self.explain(
                "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"
            )
            e.plan          # (plan generic-join (order ...) (relations ...))
            e["writes"]     # (writes transactional)

        SQL's EXPLAIN, over this engine's own decisions. A match form answers
        which seam entry handles it and with what fidelity, whether a bound
        pushes into the provider, the source, the context world, the
        annotation semiring, emission, event delivery, writes, the error mode,
        the merge policy, whether the space's source relations are
        materialised, and the PLAN: `generic-join` with the variable order and
        each conjunct's columns, `nested-loop` with the conjunct the matcher
        leads with, or `empty-factor` with the conjunct that has no candidate.
        An operation call answers its effect, whether it has an inverse, its
        annotations, its error mode and the cache decision the memo made.

        The plan names the join the engine RUNS. Deciding that costs the
        query's shape and one scan of each conjunct's relation, because a
        conjunction whose stored rows are not all ground declines the Generic
        Join and must read `nested-loop`; nothing is sorted and no trie is
        built, so explaining a triangle over 2,048 stored edges cost 7,350
        engine inferences against the query's own 237,473, and the share falls
        as the data grows: 10.1%, 4.6% and 3.1% at 128, 512 and 2,048 rows
        [measured 2026-09-07; command=PYTHONPATH=extensions/python
        python extensions/python/benchmarks/probes/explain_plan_cost.py;
        fixture=a two-out-degree ring of
        1,024 nodes at loadavg 62].

        `analyze=True` is EXPLAIN ANALYZE: the same items plus `(inferences
        N)`, `(answers N)` and `(cputime S)` measured by running the query
        inside `stats()`. It REFUSES the query when the engine can NAME an
        operation in it that writes, because an analysis that mutates is not an
        analysis; `allow_writes=True` says to measure it anyway. A match
        TEMPLATE is evaluated once per answer, so `(match &s (edge $x $y)
        (add-atom &s (seen $x)))` is a writing query.

        The longhand is the MeTTa form: `m.run("!(explain <query>)")` answers
        the same atoms, and `analyze=True` is that run with a `stats()` block
        around `eval()` of the same query. A form that is neither a match nor
        an operation call keeps the engine's own `type_error(explainable, ...)`.
        """
        return await self.call(
            lambda m: m.explain(query, analyze=analyze, allow_writes=allow_writes, **values)
        )

    async def profile(
        self,
        source: str | TemplateLike,
        /,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
        **values: Any,
    ) -> tuple[list[list[Atom]], EngineProfile]:
        """Run source under the engine's statistical profiler, answering
        (groups, profile): the groups exactly as run() answers them, and
        the profile carrying sample counters plus one row per predicate,
        self-ticks first.

            groups, prof = m.profile("!(big-computation)")
            prof.top(5)     # the five predicates the samples landed in

        A row carries the predicate's calls and redos, its ticks, the file
        and line its clauses were defined at, and its share of the sampled
        seconds. `prof.as_stats()` answers the same run as a `pstats.Stats`,
        so `sort_stats("cumulative").print_stats()` reads it and
        `dump_stats(path)` writes what snakeviz and tuna open.

        The sampler is statistical: a program that finishes in
        milliseconds carries few samples, so profile something that runs.
        Profiling changes execution; it is a debugging surface, not a
        mode to leave on.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(
            lambda m: m.profile(source, timeout=timeout, inferences=inferences, **values)
        )

    async def profile_extension(
        self,
        source: str | TemplateLike,
        /,
        *,
        extension: str | None=None,
        names: _abc.Sequence[str] | None=None,
        timeout: float | None=None,
        inferences: int | None=None,
        **values: Any,
    ) -> tuple[list[list[Atom]], list[FunctionCost]]:
        """Run source under the profiler, reporting only YOUR functions.

        `profile()` answers "which predicate did the samples land in", over
        every predicate in the process. The question a library author has is
        narrower: of the functions my library registered, which one is
        costing me, and is anything wrong with how it was installed.

            groups, costs = m.profile_extension("!(my-workload)",
                                                extension="mylib")
            for cost in costs:
                print(cost)
            # <mylib-join/3 prolog: 40100 calls, 39900 redos, 812 ticks, index 1x>

        Name the `extension` and its registered members are looked up, or
        pass `names` for an explicit list. Each row carries the tier that
        installed the function and where from, its exact call and redo
        counts, the sampler's ticks, and its clause index.

        The two columns worth reading first are `redos` and `speedup`. Redos
        on a function meant to be deterministic are a leftover choice point,
        which costs the caller about twice and is invisible to the inference
        counter. A `speedup` of 1 means no argument discriminates, so every
        call walks the clause list; `indexed` False on a function nothing has
        called much only means SWI has not built one yet.

        The sampler is statistical, so profile something that runs, and
        profiling changes execution: this is a debugging surface.
        """
        return await self.call(
            lambda m: m.profile_extension(
                source,
                extension=extension,
                names=names,
                timeout=timeout,
                inferences=inferences,
                **values,
            )
        )

    async def save(
        self,
        path: str | os.PathLike[str],
        *,
        format: SaveFormat=SaveFormat.metta,  # noqa: A002 -- the declared public parameter spelling
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> int:
        """Write every stored atom of this space, equations included, as
        MeTTa source by default. ``format="fast"`` writes a version-pinned
        image of the receiver's equation world: its own atoms, owned child
        spaces, aliases bound to those spaces, and translator rules. Loading
        the image mints fresh runtime space identities and preserves their
        graph relationships. The returned count remains the receiver's own
        atom count. Text variables are numbered by first occurrence within
        each atom, so saving unchanged content twice is byte-stable. A path
        ending .gz writes gzip compressed in either format, and load and
        import! read it back under the same name. The completed sibling file
        is synced and then atomically replaces the target, so a failed save
        leaves the old file intact. Atoms carrying live host objects cannot
        survive either file and are refused.

        `timeout` (seconds) and `inferences` (engine steps) bound the save with
        the engine's own guards, exactly as they bound load(). A text save
        examines the receiver; a fast save also traverses its reachable
        equation-world graph and registries. Those guards therefore bound all
        state the chosen format writes, and the atomic replace above makes a
        stopped save safe: the sibling is never moved into place.

        There is no `format` on load(), and that is not an omission. When you
        save, the file does not exist and something has to say which of the two
        to write; when you load, load() reads which it is, `.gz` included.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(
            lambda m: m.save(path, format=format, timeout=timeout, inferences=inferences)
        )

    async def source(self) -> str:
        """Return this space's directly stored atoms as loadable MeTTa text.

        This is exactly the text that ``save(path, format="metta")`` writes:
        one atom per line, including equations, with a final newline when the
        space is nonempty. Variables are numbered by first occurrence within
        each atom, making independent views of unchanged content byte-stable.
        Inherited prelude and library atoms, the global
        ``&metta`` catalog, and child spaces are outside that save boundary.
        Live host objects and atoms whose printed form cannot round-trip are
        refused for the same reason a text save refuses them.
        """
        return await self.call(lambda m: m.source())

    async def load(
        self,
        path: str | os.PathLike[str],
        *,
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> list[list[Atom]]:
        """Add a text program or trusted fast cache to this space.

        This is a consult, so it always loads and what it loads REPLACES
        what the same file put in this space before. Edit the file, load it
        again, and the space holds the new definitions and not both; the
        engine says on stderr which file it replaced and how many atoms
        went. Atoms from other sources, and ones you added yourself, stay.
        A load that raises leaves the previous definitions standing, so a
        broken edit costs nothing but the error.

        `!(import! &self path)` is the other form and loads a file that is
        new or edited, skipping one that is neither. The two agree on what
        a reload means and differ only in whether an unchanged file runs
        again, which is SWI's consult/1 against its if(changed).

        A .gz path is detected and read through the decompressed bytes.

        `timeout` (seconds) and `inferences` (engine steps) bound the load
        with the engine's own guards, raising TimeLimitError or
        InferenceLimitError. A load is all or nothing: a stop takes back
        everything the file had put in a space, the same way a load that
        fails on a bad form does, because a file the space holds half of is
        not a file it can replace later. run() is the entry point that
        keeps finished work when a bound stops it. This is the one most
        likely to be handed code the caller did not write, since a file can
        carry `!` directives and an import graph, so it takes the same pair
        its siblings take.

        Program text with holes is refused here. A hole is a binding, and a
        PATH has nowhere to bind one: run() takes holes, and an f-string or a
        Path builds a computed filename.
        """
        return await self.call(lambda m: m.load(path, timeout=timeout, inferences=inferences))

    async def parse(self, source: str | TemplateLike, /, **values: Any) -> Atom:
        """Read one form into an atom without evaluating it.

        Holes work here as they do at run(), and land in the term this
        answers rather than crossing to the engine, since nothing runs:
        `m.parse(t"(person {name} 36)")` is the built term with the value
        already in it.
        """
        return await self.call(lambda m: m.parse(source, **values))

    async def register_token(
        self,
        pattern: str | _re.Pattern[str],
        constructor: Callable[[str], Any],
    ) -> None:
        """Register a full-token regex and its Atom constructor.

        The constructor receives the complete matched lexeme. It may return an
        Atom or any value accepted by :func:`metta.ground`. A later registration
        of the same pattern replaces the constructor. Only future parses read
        the new mapping; atoms already returned are immutable values.
        """
        return await self.call(lambda m: m.register_token(pattern, constructor))

    async def unregister_token(self, pattern: str | _re.Pattern[str]) -> None:
        """Remove a reader-token class; an absent pattern is already removed."""
        return await self.call(lambda m: m.unregister_token(pattern))

    async def add(self, *atoms: Any) -> None:
        """Add atoms to this space, one engine round-trip for the lot.
        An (= ...) atom compiles as an equation. Every Atom shape crosses
        unchanged, including a bare Symbol, Grounded value, and empty
        Expression; a free Variable receives the engine's own
        insufficient-instantiation refusal. The MeTTa longhand is
        `!(add-atoms <space> (<atom> ...))`. It is NOT `add-atom`, which is
        upstream PeTTa's spelling and takes upstream's domain: a headless atom
        cannot become a fact in a space there, so `!(add-atom &self b)` has no
        answer on either engine. This space is wider and `add-atoms` is the
        door onto the wider part.

        A variable's NAME is not stored. `(rule $x $y)` reads back as
        `(rule $_17902 $_17904)`, because a variable is an identity and not a
        spelling. That is the right property for a logic engine and it is the
        one thing about storage that surprises everybody once.

        A library IS knowledge, so the same operator imports it: ``m += lib.he``
        performs ``!(import! <m> (library lib_he))`` with this space as the
        target. An import is an effect, so it refuses to hide inside an atom
        batch or share a call with stored atoms.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.add(*atoms))

    async def remove(self, atom: Any, *more: Any) -> bool | int:
        """Remove ONE unifying occurrence and say whether one was there,
        which is Python's own `list.remove` grain.

        Variadic like `add` and `transfer`: several atoms ride one engine
        crossing inside one transaction, and the answer counts the found,
        so the one-atom call still reads as the truth value it always
        was.

        `space -= atom` is this same grain without the report, the way
        `+=` is `add` without one: Python's in-place difference over a
        MULTISET, whose own Python spelling is `collections.Counter`,
        subtracts the multiplicity given rather than clearing the key.
        That is the only reading under which the operators are inverses,
        so `s += a; s -= a` leaves the space it found. `-=` classifies its
        operand exactly as `+=` does, so `-=` subtracts the same fact stream
        `+=` stores, one occurrence per element, in one
        transactional crossing.

        `del m[pattern]` is the draining form: it takes every
        unifying occurrence in one crossing and raises when nothing
        matched, as Python's `del` does, and MeTTa spells it `remove-atom`
        [source: engine/spaces/foreign.pl, remove_matching_atoms/2].
        MeTTa spells this method's grain `subtract-atom`. This is the one
        method that reports absence.

        A bare variable is the remove-everything reading a multiset space
        gives it, each atom leaving through its own proper path, equations
        and their compiled clauses included.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.remove(atom, *more))

    async def transfer(self, *atoms: Any, to: Space) -> int:
        """Move ONE unifying occurrence of each atom into another space.

        Variadic and atomic: however many atoms ride the call, one engine
        transaction moves them in one crossing, so a mid-move failure
        rolls every side back and nothing is lost between the spaces. The
        answer counts the moved; an absent atom moves nothing and counts
        nothing, which is ``remove``'s own found-reporting grain, so the
        one-atom call still reads as a truth value. The longhand stays
        reachable: a :meth:`transaction` around ``remove`` and ``add``
        says the same thing one atom at a time. :meth:`take` is the
        WAITING kin for a pattern.
        """
        return await self.call(lambda m: m.transfer(*atoms, to=to))

    async def atoms(self) -> list[Atom]:
        """Every stored atom in this space."""
        return await self.call(lambda m: m.atoms())

    async def peek(self, pattern: Any, *, where: Any | None=None, deadline: float | None=None) -> Atom:
        """Wait for one matching atom and leave it in this space.

        A finite deadline raises ``Timeout`` when no match arrives.

        `where` is match()'s guard on a blocking wait: a term over the
        pattern's variables, evaluated once a candidate binds them and
        required true, so "wait for a job whose priority is above five" is one
        call. Without it the guard had to live in the caller, as a wait and a
        re-wait around every candidate the guard rejected, and the deadline
        restarted each time round [measured 2026-08-31].
        """
        return await self.call(lambda m: m.peek(pattern, where=where, deadline=deadline))

    async def take(self, pattern: Any, *, where: Any | None=None, deadline: float | None=None) -> Atom:
        """Wait for and remove exactly one matching atom from this space.

        Competing takers cannot receive the same occurrence. A finite
        deadline raises ``TimeoutError`` when no match arrives. `where` is
        peek()'s guard, and it is checked BEFORE the removal, so an atom the
        guard rejects stays where it is for whoever does want it.
        """
        return await self.call(lambda m: m.take(pattern, where=where, deadline=deadline))

    @overload
    async def cast(self, type_: _builtins.type[_CastT], /) -> _CastT: ...
    @overload
    async def cast(self, type_: Atom | str, /) -> Any: ...
    @overload
    async def cast(self, value: Any, type_: _builtins.type[_CastT], /) -> _CastT: ...
    @overload
    async def cast(self, value: Any, type_: Atom | str, /) -> Any: ...
    async def cast(self, value: Any, type_: Any=..., /) -> Any:
        """Cast this space atom ambiently with one argument, or answer value
        narrowed by this space's type discipline with two arguments. The
        explicit form has the same acceptance a typed call compiles, ':'
        declarations here and &self in scope, protocol types included. A
        refusal raises metta.CastError naming the value's actual types.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.cast(value, type_))

    async def trace(
        self,
        source: Atom | str,
        max_events: int | None=None,
        *,
        filter: Symbol | str | Iterable[Symbol | str] | None=None,  # noqa: A002 -- the declared public parameter spelling
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> Trace:
        """Run a TERM, or source, under the engine's reduction trace and
        answer TraceEvent records: what entered reduction at which depth,
        what it answered, and which reductions failed (a call with no
        exit). `m.trace(S.fib(10))` is the ordinary spelling, the same
        argument `answers` and `eval` take; a string is still a string.
        What is traced executes for real, writes included, like run();
        the wrap exists only while tracing, so untraced calls pay
        nothing and the wrapping itself is not charged to the bounds
        below. max_events bounds the RECORDING and timeout,
        inferences and stack bound the RUN, defaulting to whatever
        `m.limits()` scopes; they are independent because a program can
        retire millions of inferences inside a handful of recorded
        events. Whichever one stops it, the events already recorded are
        ANSWERED and `stopped` names the bound, so a caller told a trace
        was cut knows which bound to raise.
        filter selects exact function Symbols or names, singly or in an iterable.
        None records all functions; [] records none. Selection happens before
        the recording bounds, while excluded calls still execute and add depth.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(
            lambda m: m.trace(
                source,
                max_events,
                filter=filter,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def debug(
        self,
        source: Atom | str,
        *,
        on: Any=None,
        inferences: int | None=None,
        at: int | None=None,
    ) -> Debugger:
        """Run a TERM, or source, under breakpoints, stepped from Python.

        Iterating the Debugger runs the program to each breakpoint, the loop
        body is where the program is SUSPENDED, and leaving the body resumes
        that same execution:

            with m.debug(S.quad(3), on=[S.double]) as d:
                for stop in d:
                    print(stop)      # halted here
                    if stop.depth > 2:
                        d.step()     # stop at the next reduction instead
                print(d.answers)

        on= names the functions that stop it, the way every door here names a
        head; naming none runs the program to the end in one advance.
        `step()` stops at the very next reduction, breakpoint or not, and
        lasts one advance. `breakpoints` is a live set, so one added while
        the program is suspended stops it.

        at= is the third kind of breakpoint, a COUNT: it stops at the event
        with that sequence number, numbering reductions from 0 the way a
        Recording numbers them, so `at=200` is "put me where event 200 is".
        `Recording.debug(at=k)` is the convenience over this one.

        inferences bound the WHOLE session cumulatively, so a resume that
        would never reach another breakpoint stops. There is no timeout:
        the session is suspended by design and a clock would run while a
        person reads a stop. What is debugged executes for real, writes
        included, and inherits the caller's scope. Close it, or leave its
        with-block: the session holds a wrapper on every compiled function
        until it does.
        """
        return await self.call(lambda m: m.debug(source, on=on, inferences=inferences, at=at))

    async def record(
        self,
        source: Atom | str,
        *,
        seed: int | None=None,
        max_events: int | None=None,
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> Recording:
        """Run a TERM, or source, and keep the whole run as data.

        The data walks backwards, saves to a file, and re-runs.
        `m.trace` is the rung below: it answers the events alone. A Recording
        is those events plus the state that produced them, which is what makes
        them re-runnable rather than only readable:

            rec = m.record(S.fib(12))
            rec.save("fib.metta-rec.json")
            rec.at(-1)               # the last event, with its call stack
            rec.back()               # a step backwards costs a lookup
            rec.replay(other)        # the same run, in another engine
            with rec.debug(at=17) as d:   # live, stopped where event 17 is
                print(d.stop)

        A recorded run always has a seed, minted when you do not name one,
        because a replay that cannot reproduce the draws is not a replay; the
        generator is restored afterwards. `(with-seed S expr)` is the MeTTa
        spelling of the same scope.

        max_events bounds the RECORDING and timeout and inferences bound the
        RUN, exactly as on trace(); a cut recording says so through
        `rec.events.stopped` and replays to the same length. A program whose
        effect plan reaches oracleIO is recorded with `replayable` false and
        the reason naming what it reached, and replay() then refuses rather
        than re-reading the host.
        """
        return await self.call(
            lambda m: m.record(
                source,
                seed=seed,
                max_events=max_events,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def lint(self) -> list[Finding]:
        """Diagnose this space for the silently-wrong class: declared
        types nothing defines, arity mismatches, unbound body variables,
        duplicate equations, and references no function or fact carries.
        Answers metta.lint.Finding records, empty when nothing looks
        wrong.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.lint())

    async def effect_plan(self, target: Any) -> _ops_module.EffectPlan:
        """Return operations the target may execute and their joined effect.

        The engine translates the same atom or source form ``eval`` accepts,
        follows nested compiled calls, and reads current operation metadata.
        It does not execute the target. A later registration change is visible
        on the next call. This is the analysis reified-world admission uses.
        """
        return await self.call(lambda m: m.effect_plan(target))

    async def digest(self) -> str:
        """A sha256 hex digest of this space's content: every stored atom,
        equations included, canonicalized (variables numbered, multiset
        sorted) so the same atoms answer the same digest in any insertion
        order and in any process. Two spaces agree on digest() exactly
        when save() would write the same content. Live host objects have
        no cross-process identity and are refused, like save().
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.digest())

    async def clear(self) -> None:
        """Remove everything stored here, compiled equations included."""
        return await self.call(lambda m: m.clear())

    async def match(
        self,
        *patterns: Any,
        where: Any | None=None,
        limit: int | None=None,
        timeout: float | None=None,
        inferences: int | None=None,
        under: Any=_UNSET,
        into: _builtins.type | None=None,
        **values: Any,
    ) -> Any:
        """Lazily match patterns against this space as one conjunction.

        Variables shared between patterns join, the engine's own match/4
        doing the joining. Columns are the variable names in first
        appearance order. `where` is a guard term over the same variables,
        evaluated per join and required true, so restrictions a pattern
        cannot spell (an inequality) compose onto the match:

            m.match(S.person(V.name, V.age), where=V.age.ge(18))

        `limit` bounds the answers, the engine stopping at the count
        rather than trimming afterwards. `timeout` (seconds) and
        `inferences` (engine steps) bound the whole call, raising
        TimeLimitError or InferenceLimitError when hit, for joins whose
        size is not known in advance.

        The returned Answers view pulls only what Python observes. ``bool``
        pulls one row, exact-one operations pull at most two, and slicing
        retains an Answers view. ``len`` uses an engine-side aggregate when
        no row has yet been pulled.

        ``under=`` interprets the same ask through an annotation algebra.
        ``under=counting`` answers one ``TaggedAnswer`` whose annotation is
        the engine-computed count, including duplicate derivations without
        crossing their rows into Python. Ordered carriers sort in their
        declared direction before slicing, so
        ``m.match(q, under=ranked)[:3]`` is top-k and
        ``under=tropical`` puts the cheapest annotation first. Other carriers
        answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and
        ``under(other)``; the latter two reuse the retained derivation rather
        than querying the space again. ``with metta.under(carrier)`` supplies
        the carrier when this call has no explicit ``under=``.

        `into=Rows` explicitly chooses the eager Rows face. Other `into=`
        values shape each row into a dataclass, NamedTuple, or
        TypedDict matched by field name, sqlite3's row_factory reading:
        `m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,
        and Rows stays the default so nothing is lost. A one-variable query
        whose column holds complete constructor expressions rebuilds those
        expressions instead: `m.match(V.edge, into=Edge)`.

            m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))

        A text pattern may carry HOLES, as run()'s source may:
        `m.match(t"(person {name} $age)")` matches the value itself, so a name
        holding a space stays one String atom rather than reading as two
        symbols. Keyword values apply across every pattern of the call.
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
                **values,
            )
        )

    async def solve(self, pattern: Any, subject: Any) -> Any:
        """Run relational ``let`` and return bindings keyed by its variables.

        ``solve(4, V.x - 1).x`` places the known value on let's pattern side,
        lets the arithmetic relation solve backwards, and projects ``x``.
        The answer template is derived from the pattern's variables followed
        by any new subject variables, so either relational direction can
        introduce the bindings and the third hand-written ``let`` argument
        disappears.
        """
        return await self.call(lambda m: m.solve(pattern, subject))

    async def parallel(self, *targets: Any, timeout: float | None=None) -> list[Atom | Undefined]:
        """Evaluate every target concurrently, answering every branch's answers.

        This is the engine's `hyperpose`, the parallel twin of `superpose`:
        one SWI thread per branch through concurrent_and/2, so independent
        branches cost about one branch's wall clock rather than their sum.

            m.run("(= (sq $x) (* $x $x))")
            m.parallel(S.sq(1), S.sq(2), S.sq(3))    # 1, 4 and 9, in any order

        This is the **in-engine** fan-out: one janus call, the branches split
        below it. The other route is `pool()`, the **Python-side** fan-out
        across several engines. Reach for this one when the fan-out is a MeTTa
        expression, and for `pool()` when it is a Python loop. They compose,
        so a pool worker may itself evaluate a `parallel()`.

        (Before 2026-08-15 this docstring said in-engine fan-out was the only
        route to a second core, because every janus call took one process-wide
        lock. That lock is now per-engine, and Python threads holding their own
        engine measured 1.94x, 3.90x and 7.26x at 2, 4 and 8 threads.)

        **Answers arrive in completion order, not argument order**, because
        the branches race. Compare sets rather than sequences, and evaluate a
        `superpose` instead when order carries meaning.

        Each target is a term or its source text, as everywhere else. No
        targets answers nothing without calling the engine.

        `timeout` bounds the call and is the bound to use here. There is
        deliberately no `inferences=`: the engine's inference limit counts
        the calling thread, and `concurrent_and/2` runs every branch in a
        worker, so a limit of 50,000 does not stop two branches spending six
        million [measured 2026-08-15]. An unenforceable bound is worse than
        an absent one, so eval() over a `superpose` is the way to bound this
        work by inferences, at the cost of running it on one core.
        """
        return await self.call(lambda m: m.parallel(*targets, timeout=timeout))

    async def reducible(self, target: Any) -> bool:
        """Whether a head reduces here, asked without evaluating anything.

            m.reducible(S.double(4))     # True
            m.reducible(S.Point(1, 2))   # False, nothing applies to that head

        The same head test eval_status() uses, published on its own because a
        caller who wants to DECIDE about an unreduced term should not have to
        run the term to find out. That decision is the caller's: a term
        nothing applies to is its own answer, which is ordinary MeTTa and how
        `!(hello world)` works, so there is no scope here that refuses one.

        The Node extension has had m.reducible() since it existed; Python had
        only eval_status(), which evaluates to tell you [measured 2026-08-31].
        """
        return await self.call(lambda m: m.reducible(target))

    async def eval_status(
        self,
        target: Any,
        /,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
        theory: Any | None=None,
        interpreter: Any | None=None,
        **values: Any,
    ) -> list[tuple[str, Atom | Undefined | None]]:
        """Evaluate a term, pairing each answer with how it was produced.

            m.eval_status(S.double(4))       # [("value", Grounded(8))]
            m.eval_status(S.Point(1, 2))     # [("not-reducible", Expression(...))]
            m.eval_status(S.empty())         # [("empty", None)]

        `value` means an equation, builtin or special form applied.
        `not-reducible` means no rule applied, so the answer is the term
        itself, which is what MeTTa does with any head it cannot call.
        `empty` means the goal produced no answer at all, and its atom is
        None. Reading the last two as the same thing is the mistake this
        exists to prevent: an unevaluated term and a pruned branch look
        alike from the answers alone. An error is not a status here,
        because it arrives as an exception.

        A `bind()` scope binds host values into the term exactly as it
        does for eval(), and it has to: the substitution lands BEFORE the
        reducibility question, so the status of an evaluation that binds
        anything was unaskable without it. Name keys mean symbols and atom
        keys mean themselves, so `bind({V.x: 5})` fills a variable hole.

        `theory` and `interpreter` are eval()'s own, and mean the same here.
        This is the method that says which evaluation path produced an answer, so
        being unable to point it at an alternative evaluation relation was the
        sharpest form of the gap: `m.eval_status(target, interpreter=my_eval)`
        is how you see whether an explicit interpreter reduced a term or handed
        it back. `under=` is deliberately NOT here: a carrier annotates every
        answer with an algebra value, so it would make a status row a triple
        rather than the pair it is, which is a question about what a status IS.
        """
        return await self.call(
            lambda m: m.eval_status(
                target,
                timeout=timeout,
                inferences=inferences,
                theory=theory,
                interpreter=interpreter,
                **values,
            )
        )

    async def run_status(
        self,
        source: str,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> list[list[tuple[str, Atom | Undefined | None]]]:
        """run(), with each directive's answers paired with how they arose.

        The grouping and the answers are run()'s own; see eval_status() for
        what the three paths mean.
        """
        return await self.call(
            lambda m: m.run_status(source, timeout=timeout, inferences=inferences)
        )

    async def one(self, target: Any, *, timeout: float | None=None, inferences: int | None=None) -> Any:
        """Return the sole answer as a plain Python value for internal callers.

            m.eval(S.fact(5))[0]         # Grounded(120)

        Exactly one answer is the contract: none or several raise naming
        the count, because a caller asking for the value has asserted
        there is one. Grounded answers unwrap to their Python values;
        symbols and structure stay atoms.

        This is one point on the answer-cardinality axis, spelled the
        same everywhere it appears: eval() takes every answer (MeTTa's
        collapse), while this private helper demands exactly one. The same
        timeout/inferences bounds apply throughout.

        An `(Error ...)` answer raises MettaResultError carrying the
        atom: an error among the answers is the evaluation reporting
        failure, and failure outranks the count. eval() is the method
        that keeps errors as data.
        """
        return await self.call(lambda m: m._one(target, timeout=timeout, inferences=inferences))

    async def first(
        self,
        target: Any,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> Any:
        """The first answer as a plain Python value, or None for no answers.

        The tolerant member of one()'s family: one() asserts exactly
        one, eval() answers all, first() answers the first or nothing,
        decoded by the same rule as one(). An Undefined first answer
        still raises, since None here MEANS no answers. Tolerance is
        about cardinality, not content: a first answer that is an
        `(Error ...)` atom raises MettaResultError exactly as one()
        does, because None must keep meaning "no answers" and an error
        used as a value is the silent kind of wrong.
        """
        return await self.call(lambda m: m._first(target, timeout=timeout, inferences=inferences))

    # pure DIVERGES from Space.pure, because
    # the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the
    # worker would register on the caller's thread rather than the engine's. Only the applied form
    # crosses
    async def pure(self, fn: Callable, /, **options: Any) -> Any:
        """An operation whose answer depends only on its arguments.

            @m.pure
            def double(x: int) -> int:
                return 2 * x

        The cache-safe class, and the only one memoization and tabling admit
        without an explicit policy.

        A GENERATOR written this way is lifted to `nondeterministicReadOnly`,
        because a generator is nondeterministic whatever it declares, and the
        registration reads that off the function rather than asking. The lift
        only ever raises the rank, so it widens the answer-count claim and
        never weakens the effect claim -- but it does mean a generator is not
        cache-safe, which is the whole reason it is lifted out of this class
        [tested: test_a_generator_is_lifted_to_the_nondeterministic_rank;
        commit=7e5091540a8dc0903bcee24f3e5b8b85a19f805f].

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return await self.call(lambda m: m.pure(fn, **options))

    # reads DIVERGES from Space.reads, because
    # the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the
    # worker would register on the caller's thread rather than the engine's. Only the applied form
    # crosses
    async def reads(self, fn: Callable, /, **options: Any) -> Any:
        """An operation that reads stable state without changing it.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return await self.call(lambda m: m.reads(fn, **options))

    # writes DIVERGES from Space.writes, because
    # the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the
    # worker would register on the caller's thread rather than the engine's. Only the applied form
    # crosses
    async def writes(self, fn: Callable, /, **options: Any) -> Any:
        """An operation that changes engine or host state.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return await self.call(lambda m: m.writes(fn, **options))

    # io DIVERGES from Space.io, because
    # the sync method's fn=None form returns a DECORATOR, and a decorator handed back across the
    # worker would register on the caller's thread rather than the engine's. Only the applied form
    # crosses
    async def io(self, fn: Callable, /, **options: Any) -> Any:
        """An operation that observes an external oracle.

        A clock, randomness, a network, a file, another runtime.

            @m.io
            def now() -> float:
                return time.time()

        The fail-closed top of the lattice. Declare it when what the operation
        reaches is decided at run time or by a library the engine cannot bound.

        Every ``op`` keyword applies: ``name``, ``arities``,
        ``declarations``, ``inverse`` and ``transport``. They arrive as
        ``**options`` and forward unchanged, so the signature above shows
        the mechanism and this line shows the surface.
        """
        return await self.call(lambda m: m.io(fn, **options))

    async def unregister_op(self, name: str) -> None:
        """Remove a registered operation, every arity of it.

        An absent name raises KeyError, as convert.unregister_type does:
        removing something that was never there is a mistake worth hearing
        about, not a no-op to absorb.
        """
        return await self.call(lambda m: m.unregister_op(name))

    async def builtins(self) -> list[str]:
        """Every function callable from this space, plus every special form.

        Its own equations, the ones it inherits, ``&self``'s shared ones and
        the engine's builtins, with the translator's special-form heads,
        sorted without duplicates. A head another space defines is
        registered process-wide (the translator's call-or-data question,
        which ``is_function`` answers) but is not callable here and is not
        listed here.
        """
        return await self.call(lambda m: m.builtins())

    async def is_function(self, name: str) -> bool:
        """Report whether the name is registered as a function anywhere.

        This is the translator's call-or-data question and holds wherever a
        term compiles; ``is_function_here`` asks whether the head answers
        from THIS space, and ``builtins()`` lists what this space can call.
        """
        return await self.call(lambda m: m.is_function(name))

    async def is_function_here(self, name: str) -> bool:
        """Whether a function would answer from THIS space: it has clauses
        this space's module sees, its own or the shared ones in user.
        Another space's equations are invisible here and do not count.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.is_function_here(name))

    async def arities(self, name: str) -> list[int]:
        """Compiled predicate arities for a name: MeTTa arity plus one each."""
        return await self.call(lambda m: m.arities(name))

    async def register_prolog(
        self,
        source: str | None=None,
        *,
        path: str | os.PathLike[str] | None=None,
        names: _abc.Sequence[str] | _abc.Mapping[str, str]=(),
    ) -> tuple[str, ...]:
        """Register Prolog predicates as MeTTa functions, at native speed.

        This is the extension point for a library that wants to run fast.
        op() is the one most people find first, and every call it
        serves crosses the janus boundary: 25.16 inferences and 2.34us per
        call, against 7.16 inferences and 0.13us for the same operation
        written in Prolog [measured 2026-08-15, 3000 calls in one harness].

        Read the microseconds, not the inferences. The crossing counts as ONE
        inference and costs real time, so inferences say a Python operation is
        3.1x a Prolog one while wall clock says 18x. That is a fine price for
        reaching NumPy or an LLM and a bad one for arithmetic in a loop.

        A registered predicate keeps its nondeterminism: one that offers three
        solutions gives the MeTTa function three answers.

        A predicate follows the compiled calling convention, inputs first and
        one output last:

            m.register_prolog(
                "'vec-dot'(A, B, Out) :- ... .",
                names=["vec-dot"],
            )
            m.eval("(vec-dot (1 2) (3 4))")[0]

        or, for a library shipping a file beside its Python:

            m.register_prolog(path=Path(__file__).parent / "fast.pl",
                              names=["vec-dot", "vec-norm"])

        Every name is registered explicitly rather than discovered, because
        registering a name whose predicate is absent records no arity and then
        compiles every call to it into a partial application instead of
        failing, which is a silent wrong answer rather than an error. This
        raises instead: a name with no predicate behind it is refused before
        it can do that.

        The refusals are the engine's, through check_prolog_function_names/3
        and import_prolog_functions/2, so this and the MeTTa spelling enforce
        one rule rather than two copies of it. Three names are refused: one
        with no predicate behind it, a builtin, and a special form.

        Nothing is registered unless every name can be, so a typo in the list
        changes nothing. The consulted SOURCE does stay loaded on failure,
        which is deliberate rather than overlooked: loading it again is the
        retry, and it is idempotent, since the source is identified by a hash
        of its own content.

        **This is a method on a space and it registers PROCESS-WIDE.** So do
        op and define. Only equations are space-scoped, so an anonymous
        space() isolates one of the three things you can register and
        shares the other two. That is deliberate rather than overlooked: a
        Prolog predicate lives in `user`, every space has to be able to call
        it, and a library loaded inside a named space would define itself
        where the registration could not see it. The method sits on the space
        because that is where the rest of the surface is, not because the
        registration is scoped to it.

        The name is owned by one tier. A second registration of the same name
        from another tier is refused, in both directions, naming the owner, so
        two libraries cannot silently take the same name from each other.

        A parameter a MeTTa caller should reach unevaluated needs a type
        declaration, which this call does not take yet:

            m.register_prolog("'shape-of'(A, Out) :- Out = [shape, A].",
                              names=["shape-of"])
            m.run("(: shape-of (-> Atom Atom))")
            m.eval("(shape-of (+ 1 2))")[0] # (shape (+ 1 2)), not (shape 3)

        Declare it BEFORE anything calls the function. A call site compiled
        while the declaration is absent keeps evaluating the argument even
        after it lands.
        """
        return await self.call(lambda m: m.register_prolog(source, path=path, names=names))

    async def register_foreign_library(
        self,
        path: str | os.PathLike[str],
        *,
        entry: str | None=None,
        names: _abc.Sequence[str]=(),
    ) -> tuple[str, ...]:
        """Load a compiled `.so` and register its predicates as MeTTa functions.

        The C tier is the cheapest one on this page's cost table, one
        inference per call, and reaching it used to mean hand-writing two
        Prolog directives into `register_prolog`:

            m.register_foreign_library(Path(__file__).parent / "cbump.so",
                                       entry="install_cbump", names=["c-bump"])

        `entry` is the C initialiser, `install_cbump` in
        `install_t install_cbump(void)`; leave it out for a library whose
        entry is plain `install`.

        The path is resolved to an ABSOLUTE one here, which is the trap this
        exists to close: `use_foreign_library/2` accepts a path relative to
        the working directory, resolves it, and SWI deprecates that and warns
        on every load, so a library that shipped one worked from the repo root
        and warned or failed anywhere else. A file that is not there is
        refused here rather than inside the engine's loader.

        Everything after the load is `register_prolog`, so the same refusals
        apply: a name with no predicate behind it, a builtin, a special form,
        and a name another tier owns.
        """
        return await self.call(lambda m: m.register_foreign_library(path, entry=entry, names=names))

    async def register_library_path(self, directory: Any, name: str) -> None:
        """Point MeTTa at a directory of files your package ships.

            # in your package's __init__
            m.register_library_path(Path(__file__).parent / "prolog", "pettorch")

        Subject first, as every register_* call: the directory being
        registered, then the library name it serves.

        `(library pettorch fast.pl)` then resolves, from MeTTa and from
        `register_prolog(path=...)`. Without it a pip-installed library is
        under neither `<engine>/../lib` nor a git checkout, so it has to pass
        absolute paths and compute them from `__file__` by hand.

        This is SWI's own `file_search_path/2`, so an alias registered here is
        one every SWI tool already understands, and aliases compose: the
        second argument of one may be another alias. Registering the same
        directory twice is a no-op; a directory that is not there is refused
        here rather than at the first import that needs it.
        """
        return await self.call(lambda m: m.register_library_path(directory, name))

    async def unregister_prolog(self, extension: str) -> tuple[str, ...]:
        """Release everything one extension registered, and its clauses.

        The unit is the extension, not the name. `register_prolog` used to
        load a bunch of loose predicates: the engine recorded that each name
        was a function and nothing at all about the library it came from, so
        there was no uninstall to write and a partly-failed registration left
        debris nobody could enumerate.

            :- metta_extension(pettorch, [version('0.3.1')]).
            :- metta_export("(: vec-dot (-> Number Number Number))").

            m.register_prolog(path="fast.pl")     # names come from the file
            m.unregister_prolog("pettorch")       # everything it installed

        PostgreSQL's rule, and its reason: an individual member cannot be
        dropped on its own, only the whole extension, which is what stops one
        registry keeping a claim on a name another route already replaced.
        The clauses go too, through SWI's own `unload_file/1`, so a name is
        not left callable through a predicate nothing records.

        Answers the names it released. Raises when no extension of that name
        is loaded, rather than reporting success for a no-op.
        """
        return await self.call(lambda m: m.unregister_prolog(extension))

    async def derivation(
        self,
        target: Any,
        depth: int | None=None,
        *,
        timeout: float | None=None,
        inferences: int | None=None,
    ) -> list[Any]:
        """Every proof of an answer, as trees in MeTTa terms.

        Each tree names the equations that fired and the stored atoms at the
        leaves, read from the translated_from links the engine keeps for
        every compiled clause. Meta-interpreted, so slower than evaluation;
        a diagnostic, not an evaluation path. The default walks each proof
        without a depth cutoff. A positive depth returns a partial tree with
        Truncated nodes when its budget ends, so an empty list means no proof.
        `timeout` and `inferences` guard the whole search. An evaluation error
        inside a proof surfaces as itself rather than as an empty proof list.

        Building a proof executes every premise it records, including
        effectful operations. Engine writes persist and repeated derivations
        accumulate them, just as repeated evaluations do. Use
        ``with space.speculative():`` when the proof should return while its
        engine writes are discarded. That scope cannot undo Python side
        effects, I/O, or subscription callbacks that already fired, so do not
        derive an effectful target when those effects must not happen.

        A `bind()` scope binds host values into the term, for the reason
        eval_status needs it: the substitution lands BEFORE the search, so the
        proof of an evaluation that binds anything was unaskable. Name keys
        mean symbols and atom keys mean themselves, so `bind({V.x: 5})` fills
        a variable hole. It takes no `theory` or
        `interpreter`, because a meta-interpreted diagnostic does not select an
        evaluation relation.
        """
        return await self.call(
            lambda m: m.derivation(target, depth, timeout=timeout, inferences=inferences)
        )

    async def why(self, pattern: Any, *, where: Any | None=None) -> str:
        """Why a pattern matches nothing here, in words.

        Checks the cheap explanations in order: unknown function, wrong
        arity, no stored atoms with that head. Honest when it cannot tell,
        and honest about the PREMISE too: a pattern that does match is a
        question with a false premise, and this refuses it the way
        Answers.why() always did rather than answering it. Asking why
        `(job $id $pri)` matched nothing, when it matches two atoms, used to
        answer "2 job atom(s) exist here but none unifies with it"
        [measured 2026-08-31].

        `where` is match()'s guard, and asking with one is where the answer
        gets interesting: a query can be empty because the pattern found
        nothing OR because the guard rejected everything it found, and only
        the guarded question can tell you which.

        One implementation, because there were two and they agreed word for
        word on every genuine miss while disagreeing about the premise.
        """
        return await self.call(lambda m: m.why(pattern, where=where))

    async def type(self, atom: Any) -> Atom:
        """Return this space's first ``get-type`` answer, including undefined."""
        return await self.call(lambda m: m.type(atom))

    async def infer_types(self, *, declare: bool=False) -> list[Atom]:
        """Propose a `(: head (-> ...))` for every head here that has none.

            m.infer_types()                 # the proposals, nothing added
            m.infer_types(declare=True)     # add exactly those proposals

        One walk of the stored atoms names the narrowest kind covering the
        children observed at each argument position: all numbers `Number`,
        all strings `String`, all booleans `Bool`, all symbols `Symbol`, all
        expressions sharing one head that head's declared result type when it
        has one and `Expression` otherwise, mixed `Atom`. A variable observed
        at a position stands for anything and constrains nothing, so a
        position with only variables is `%Undefined%`. That is
        `pandas.api.types.infer_dtype` moved from a column's values to an
        argument position's children, its `skipna` included.

        An equation head's RESULT is what its body answers: a literal's own
        type, or the declared result of the head the body calls, which is how
        `(= (double $x) (* $x 2))` proposes `(-> %Undefined% Number)`.
        Anything else, a bare symbol included, is `%Undefined%`, because a
        symbol's own type is `%Undefined%` here too. A head observed at two
        arities gets one proposal per arity, and a head this space already
        declares gets none.

        `declare=True` adds exactly the returned atoms and nothing else, so
        `get-type` then answers them. One thing changes with the program's
        BEHAVIOUR and is worth reading before a proposal is accepted: `Atom`
        in an argument position is a metatype and stops the engine evaluating
        that argument, so a mixed position turns `(f (+ 1 2))` from `3` into
        the term `(+ 1 2)` [measured 2026-09-07]. Proposing and adding are
        two calls for that reason.

        Cost is O(atoms x arity): one pass over the space, plus one type
        lookup per distinct head. `metta.stubs()` and `inspect.signature()`
        show the same arrows, marked inferred, without adding anything.
        """
        return await self.call(lambda m: m.infer_types(declare=declare))

    async def doc(self, atom: Any) -> Atom:
        """Return this space's structured ``get-doc`` answer for one subject.

        The answer is the ``(@doc ...)`` atom the engine holds for the
        subject, whether it was documented in MeTTa source or built from a
        Python docstring:

            m.doc(S.area)
            # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)

        A subject with no documentation raises, exactly as ``type`` raises
        for a subject ``get-type`` cannot answer.
        """
        return await self.call(lambda m: m.doc(atom))

    async def integrate(self, target: Any) -> str:
        """Install a library integration; see metta.integrate."""
        return await self.call(lambda m: m.integrate(target))

    async def handles(
        self,
        pattern: str | Atom,
        fidelity: Fidelity,
        *,
        det: Determinism | None=None,
    ) -> Atom:
        """Declare how faithfully a space answers queries of one shape.

        The declaration is one (handles ...) atom in &metta, and queries
        are routed by the most specific declared shape that matches:
        Exact licenses pushing the caller's bound to the provider, Partial
        and Sound stay candidates the engine re-unifies, and Refuse makes
        the query a loud error instead of a silent partial answer. Write
        (in $x) at a position to match only queries arriving with it
        bound, so a scan-only source is three words:

            rows.handles("(edge (in $a) $b)", "Refuse")

        Coherence is checked eagerly in the same transaction as the
        write: a new entry that can disagree with an existing one on some
        query fails here, naming both, rather than on the first query
        that falls into their overlap. The atom is returned; removing it
        from &metta withdraws the declaration.
        """
        return await self.call(lambda m: m.handles(pattern, fidelity, det=det))

    async def annotations(
        self,
        subject_or_algebra: str,
        algebra: str | None=None,
        *,
        capabilities: _abc.Iterable[str]=(),
    ) -> Atom:
        """Declare the algebra a context's answer annotations live in.

        A context is a space name or an operation name. bool is the
        default at which everything vanishes; ranked admits ordered
        annotations, which is what (top k ...) consumes. A custom name must
        first be introduced with :meth:`algebra`. A one-argument call uses
        this space as the context; the two-argument form keeps an operation
        context as the explicit first subject. Capabilities are
        checked against the algebra's requirements before the catalog write;
        amplitude programs, for example, must explicitly declare ``finite``,
        ``contractive`` and ``staged`` [tested:
        test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
        commit=f88aa8be03cb64cb59d3307515ded8701f418321]. Declaring replaces any earlier row for the
        context, so the reader never meets two disagreeing atoms.
        """
        return await self.call(
            lambda m: m.annotations(subject_or_algebra, algebra, capabilities=capabilities)
        )

    async def algebra(
        self,
        name: str,
        *,
        combine: str,
        extend: str,
        zero: Any,
        one: Any,
        laws: _abc.Iterable[str]=(),
        carrier: _abc.Iterable[Any]=(),
        type: Any=None,  # noqa: A002 -- the declared public parameter spelling
        requires: _abc.Iterable[str]=(),
        order: SemiringOrder | None=None,
    ) -> Atom:
        """Declare operations with carrier membership and optional checked laws.

        ``type`` accepts a Python type, MeTTa type atom, or Boolean predicate
        and checks every input and result. A type alone grants no laws or
        fusion. ``carrier`` enumerates the finite domain required for exhaustive
        law checking; it may accompany ``type`` to constrain that domain.
        Use ``prov`` and ``.under()`` to reinterpret uncertified tensor traces.
        """
        return await self.call(
            lambda m: m.algebra(
                name,
                combine=combine,
                extend=extend,
                zero=zero,
                one=one,
                laws=laws,
                carrier=carrier,
                type=type,
                requires=requires,
                order=order,
            )
        )

    async def covers(self, effect: EffectClass | str) -> Atom:
        """Declare the strongest effect this reified world can handle.

        Coverage is a catalog fact ``(covers <space> <effect>)``. World
        evaluation always admits pureStructural plans. A stronger joined plan
        runs only when this declaration is at least as strong; redeclaring
        replaces the previous row atomically.

            orders.covers("writesState")
            world = orders.reify()
        """
        return await self.call(lambda m: m.covers(effect))

    async def compensates(self, operation: str, compensation: str) -> Atom:
        """Declare one recovery operation for an effectful operation.

        The catalog row is ``(compensates operation compensation)``. The
        source operation must already be registered at writesState or
        oracleIO, because weaker operations leave no saga receipt. The
        recovery name must already be a host operation or compiled MeTTa
        function. It receives the complete ``(did ...)`` receipt. The runner writes
        the call as ``(quote <receipt>)`` so the receipt is not evaluated
        on the way in; the quote is a barrier and does not survive, so the
        handler is handed the receipt itself.
        Redeclaring replaces the old row atomically.
        """
        return await self.call(lambda m: m.compensates(operation, compensation))

    async def add_tagged_fact(self, tag: Any, proposition: Any) -> Atom:
        """Store ``(fact tag proposition)``, the normative annotation form."""
        return await self.call(lambda m: m.add_tagged_fact(tag, proposition))

    async def add_tagged_rule(self, tag: Any, head: Any, *premises: Any) -> Atom:
        """Store one rule generated by the algebra-agnostic tag threader."""
        return await self.call(lambda m: m.add_tagged_rule(tag, head, *premises))

    async def image(self, type_name: str, setting: ImageMode) -> Atom:
        """Choose how one Python type crosses one context boundary.

        opaque carries the live object by identity; transparent projects its
        structural MeTTa image; auto makes that choice from the value's size
        and replayability. A later declaration for the same context and type
        replaces the earlier one, so an attached provider reads one policy.
        Use ``_`` as the type name for a context-wide fallback.
        """
        return await self.call(lambda m: m.image(type_name, setting))

    async def sample(self, query: str | Atom, *, k: int=10, seed: int=7) -> list[Atom]:
        """Choose ``k`` tagged alternatives with replacement by ``(rate n)``.

        The argument names and list result follow ``random.choices``. A local
        seeded generator makes repeated calls reproducible without changing
        Python's process-global random state.
        """
        return await self.call(lambda m: m.sample(query, k=k, seed=seed))

    async def consumption(self, kind: SourceKind) -> Atom:
        """Declare a space's consumption discipline.

        repeated is the default: the source re-enumerates. linear is a
        one-shot source, a cursor or a feed: its SECOND consumption is a
        loud error naming the space, where the undeclared floor answers a
        silently empty set from the drained object; re-registering the
        provider resets the mark, because a fresh provider is a fresh
        source. peek promises reads do not consume, which the conformance
        kit checks by enumerating twice. The Python door is named
        ``consumption`` so ``source()`` can show program text; the MeTTa
        catalog row deliberately keeps its language-level ``source`` head.
        """
        return await self.call(lambda m: m.consumption(kind))

    async def on_error(
        self,
        subject_or_pattern: str | Atom,
        pattern_or_mode: str | Atom,
        mode: OnError | None=None,
    ) -> Atom:
        """Declare what a context's failure becomes, per query shape.

        abort is the undeclared floor: the provider's error propagates.
        keep delivers the failure as one (Error <query> <reason>) answer
        beside the answers that already streamed, the language's own
        error-as-alternative reading. empty ends the stream silently, BY
        declaration, which is what separates it from a swallowed error.
        Shapes route most-specific-first exactly as (handles ...) entries
        do. Control signals and transport failures are never kept or
        emptied: an interrupt is the caller's, and an absent backend has
        said nothing about the data.
        """
        return await self.call(lambda m: m.on_error(subject_or_pattern, pattern_or_mode, mode))

    async def merge(self, pattern: str | Atom, policy: AnswerPolicy) -> Atom:
        """Declare how the engine merges one query shape's answers
        ACROSS contexts, for the multi-context idiom
        (match (superpose (&a &b)) ...).

        depth is today's space-after-space order and the undeclared
        floor. fair interleaves the streams round-robin. best-first is a
        k-way ordered merge by annotation, sound only when every merged
        context declares (emits <ctx> best-first), and loudly refused
        without. Shapes route most-specific-first as everywhere.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.merge(pattern, policy))

    async def context(self, world: World) -> Atom:
        """Record what a space's absence means.

        Negation as failure reads absence as falsity, which is only
        sound over a world the answerer holds whole, so a negated goal
        may consult a foreign space only when it declares closed-world;
        an undeclared one refuses under negation loudly. Native spaces
        are the engine's own database and closed by construction.
        """
        return await self.call(lambda m: m.context(world))

    async def agenda(self, policy: AgendaPolicy, function: str | None=None) -> Atom:
        """Declare which reaction fires first when several match one write.

        declaration is the default and the order they were declared, which is
        what the engine produced by accident before this was a policy;
        recency is the most recently declared first; specificity is the most
        tests in the pattern first; priority reads each reaction's own
        declared number, highest first; and user names a MeTTa function that
        SCORES a reaction, highest first. Every policy breaks ties on
        declaration order.

            alarms.reacts("(alert $w)", "(insert &log (all $w))")
            alarms.reacts("(alert fire)", "(insert &log (fire))", priority=9)
            alarms.agenda("priority")
        """
        return await self.call(lambda m: m.agenda(policy, function))

    async def reacts(self, pattern: str | Atom, operation: str | Atom, priority: int | None=None) -> Atom:
        """Declare a reaction, stored as an (on ...) atom: when an atom
        matching PATTERN lands in the space, OPERATION runs under the
        match's bindings.

        The managed heads are (insert <ctx> <atom>), (retract <ctx>
        <atom>) and (revise <ctx> <old> <new>), engine-routed rules
        going through the same write paths as direct writes. Declaring
        installs the engine's write hook, which is why reactions go
        through here or metta_install_bridges rather than a bare
        add-atom.

        A subscription bridge is the NEIGHBOUR, not a special case of this:
        a reaction's operation runs engine-side, so it reaches registered
        spaces, while the bridge rule delivers Python-side to anything
        with add and remove, an unregistered or remote target included.
        Same multi-context-systems idea, two delivery tiers.
        """  # noqa: D205 -- preserve the declared documentation
        return await self.call(lambda m: m.reacts(pattern, operation, priority))

    async def admits(self, type_name: str) -> Atom:
        """Type a pool's membership: only TYPE-carrying atoms enter.

        A thread pool is a space whose atoms are spaces, and this is its
        declaration: (admits &pool Space) plus per-atom (: <space> Space)
        declarations make membership a type judgement the ontology
        already knows how to make.
        """
        return await self.call(lambda m: m.admits(type_name))

    async def capacity(self, limit: int) -> Atom:
        """Bound a pool: an add beyond LIMIT atoms is refused loudly."""
        return await self.call(lambda m: m.capacity(limit))

    async def atomicity(self, atomicity: Atomicity) -> Atom:
        """Declare what a space's writes promise inside a transaction.

        Named for what it declares rather than for the atom it stores, which
        stays `(writes <ctx> ...)`: `writes` on a Space is the effect
        decorator for an OPERATION, and one object cannot spell two concepts
        one way.

        transactional providers implement metta.foreign.Transactional and
        are committed or rolled back WITH the engine's transaction;
        best-effort is the author's declared acceptance of a write that
        survives a rollback; atomic-single refuses transactional writes.
        Undeclared spaces refuse them loudly too, because a foreign write
        silently surviving a rolled-back transaction is the wrong answer
        the declaration exists to replace.
        """
        return await self.call(lambda m: m.atomicity(atomicity))

    async def emits(self, policy: AnswerPolicy) -> Atom:
        """Declare the order a context emits its own answers in.

        best-first is the promise (top k ...) needs before its bound may
        reach the provider: the first k of a best-first emission ARE the
        k best. Distinct from the (merge <pattern> <policy>) strategy,
        which is how the ENGINE merges answers across several contexts.
        """
        return await self.call(lambda m: m.emits(policy))

    async def events(
        self,
        delivery: Delivery | None=None,
        order: EventOrder=EventOrder.unordered,
    ) -> Atom | Any:
        """Return the event stream, or declare what this context promises.

        Subscribability is a promise about the context, not something its
        methods alone establish. A native space needs no declaration:
        every write into it runs the engine's own hooks, so it delivers
        per-write-exactly and ordered by construction. A FOREIGN context
        declares, and one that declares nothing refuses a subscription
        instead of serving one that silently misses writes.

            shared.events("at-most-once")   # redis pub/sub
            mirror.events("per-write-exactly", "ordered")

        delivery is at-most-once, at-least-once or per-write-exactly, and
        order is ordered or unordered, defaulting to unordered because an
        omitted promise is the weaker one. A Python provider says the same
        thing by overriding delivers(), which registration writes here.
        """
        return await self.call(lambda m: m.events(delivery, order))

    async def live(
        self,
        *query: Any,
        on: SubscriptionEdge=SubscriptionEdge.both,
        strategy: str | None=None,
    ) -> Any:
        """Maintain a query's multiset through this space's committed writes.

        The returned Live owns its subscriptions. close() releases them, and
        changes() reads its progress and deltas. strategy selects pattern, heads,
        or tabled maintenance; omitting it selects from the query's shape.
        """
        return await self.call(lambda m: m.live(*query, on=on, strategy=strategy))

    # ------------------------------------------ end of generated mirror

    # -------------------------------------------------------------- lifecycle

    async def _release_subscriptions(
        self, subscriptions: tuple[_AsyncSubscription | _EvaluationGroup, ...]
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
        self, subscriptions: tuple[_AsyncSubscription | _EvaluationGroup, ...]
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

    def stop(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronously cancel streams and stop without an event loop."""
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

    async def run(self, target: Any) -> list[Atom | Undefined]:
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

    def __len__(self) -> int:
        """A world is a frozen space-state, so it counts like one."""
        return len(self._world.atoms)

    def __iter__(self):
        """Iterate the frozen multiset, no engine crossing."""
        return iter(self._world.atoms)

    def __contains__(self, atom: object) -> bool:
        """Multiset membership over the frozen state, like a space."""
        return atom in self._world.atoms

    async def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> tuple[list[Atom | Undefined], AsyncWorld]:
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


_EXHAUSTED: Final[object] = object()
_STREAM_CLOSED: Final[object] = object()


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
        on: SubscriptionEdge,
        queue_max: int | None = None,
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
        self._orphaned = False
        self._dropped = 0
        self._opening = asyncio.Lock()
        self._state_changed = threading.Condition()
        self._acquiring = False

    def _offer(self, events: asyncio.Queue[Any], event: Any) -> None:
        """Hand one event to a consumer that may have stopped consuming.

        The writer is on another thread and the queue is filled through
        call_soon_threadsafe, so a full queue cannot raise back at whoever
        wrote: by the time this runs the write has returned. What it can do
        is refuse to lose the event quietly. Every event already queued is
        still delivered, and the stream then ends by raising, which is the
        gap being reported rather than papered over.
        """
        if self._closed:
            return
        try:
            events.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped += 1

    def _retire_closed_loop(self) -> None:
        """Cancel the engine fold whose asyncio delivery target is gone.

        Python documents RuntimeError as call_soon_threadsafe's closed-loop
        outcome. Cancellation is safe inside the fold's own callback because
        the registry waits only for deliveries on other threads.
        https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.call_soon_threadsafe
        """
        with self._state_changed:
            self._orphaned = True
            subscription = self._subscription
        if subscription is None:
            # Registration has published the fold but not yet returned it to
            # _ensure. That path observes _orphaned as soon as it assigns the
            # handle and performs this same retirement.
            return
        try:
            subscription.cancel()
        except Exception:
            # Keep the child tracked so owner.aclose()/stop() can retry. Its
            # callback is now inert, so later writes remain usable meanwhile.
            logger.exception(
                "could not retire an async subscription whose event loop closed"
            )
            return
        with self._state_changed:
            if self._subscription is subscription:
                self._subscription = None
            self._closed = True
            self._state_changed.notify_all()
        self._am._forget_subscription(self)

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
                    with self._state_changed:
                        if self._closed or self._orphaned:
                            return
                    try:
                        loop.call_soon_threadsafe(self._offer, events, event)
                    except RuntimeError:
                        if not loop.is_closed():
                            raise
                        self._retire_closed_loop()

                pattern, on, am = self._pattern, self._on, self._am
                where = self._where
                am._track_subscription(self)
                with self._state_changed:
                    self._acquiring = True
                try:
                    subscription = await _acquire(
                        am.call(
                            lambda m: m.subscribe(
                                pattern, deliver, on=on, where=where
                            )
                        ),
                        lambda acquired: am._subscription_call(
                            lambda _m: acquired.cancel()
                        ),
                    )
                    with self._state_changed:
                        self._subscription = subscription
                        orphaned = self._orphaned
                except BaseException:
                    am._forget_subscription(self)
                    raise
                finally:
                    with self._state_changed:
                        self._acquiring = False
                        self._state_changed.notify_all()
                if orphaned:
                    self._retire_closed_loop()
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
        async with self._opening:
            with self._state_changed:
                subscription = self._subscription
            if subscription is not None:
                await self._am._subscription_call(
                    lambda _m: subscription.cancel()
                )
            with self._state_changed:
                self._subscription = None
                self._closed = True
                self._state_changed.notify_all()
            self._am._forget_subscription(self)
            if self._queue is not None:
                self._end(self._queue)

    def _stop(self) -> None:
        """Release the engine fold from synchronous AsyncMeTTa.stop()."""
        with self._state_changed:
            self._state_changed.wait_for(lambda: not self._acquiring)
            subscription = self._subscription
        if subscription is not None:
            subscription.cancel()
        with self._state_changed:
            self._subscription = None
            self._closed = True
            self._state_changed.notify_all()
        self._am._forget_subscription(self)

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
