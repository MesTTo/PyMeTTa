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
  - interrupt_if_running throws the same reserved structured exception as
    shim resource guards [tested test_aio_interrupt_stops_the_running_evaluation]
  - close refuses new work, interrupts a running request, rejects queued
    requests, and bounds the worker join [tested test_aio_close_interrupts_work]
  - the transition drain discards only a structured interrupt and fails
    closed on every other error [tested
    test_aio_drain_only_discards_structured_interrupt]
  - an abandoned live owner emits ResourceWarning and registered workers
    detach during interpreter shutdown [tested test_aio_leak_warns_and_stop_joins,
    test_aio_shutdown_handler_stops_forgotten_workers]
  - interpreter shutdown attempts every worker and reports all expected
    stop failures together [tested test_aio_shutdown_handler_attempts_every_worker]
  - interpreter shutdown without live workers does not initialize the
    optional engine bridge [tested test_aio_empty_shutdown_does_not_import_janus]
  - async names and save formats retain the synchronous surface's contextual
    types [tested test_public_context_types_are_distinct]
  - async declaration methods reuse the catalog-generated policy aliases and
    own no duplicate Literal lists [tested: tests/check_policy_inventory.py;
    commit=0d90e628b1f90c4b4464a2907efcb357d74b13d3]
  - async cast preserves a concrete target class as its static return type and
    keeps the target positional-only [tested
    test_target_type_overloads_preserve_the_requested_class,
    test_cast_target_is_positional_only]
  - async new_space forwards inheritance, restriction, and grants on the
    owning worker [tested test_async_new_space_forwards_restriction_and_grants;
    commit=6a08901f4125c2536f5b4032daac9937f793870f]
  - reader-token registration and removal run on the owning engine worker and
    mirror the synchronous surface [tested:
    test_aio_plain_methods_forward_on_the_worker; commit=2c741dda928a30d0ce1c7e1fcf0b263b4d1bb97b]
  - async eval mirrors the synchronous single answer shape without a
    residuals flag [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=affc981bd744563f65f595259b8a3564b9d84ba9]
  - execution-policy scopes cross the worker hop and never change awaited
    return shapes [tested:
    test_no_decorator_flag_changes_the_return_shape_and_declarations_are_atoms;
    commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
  - declare_image reaches the synchronous declaration owner on the engine
    worker [tested: test_aio_covers_the_whole_synchronous_surface;
    commit=24532816d8f3987cc56059fadf3666a387ae1156]
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
import contextvars
import logging
import math
import os
import queue
import threading
import warnings
import weakref
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Final, Literal, Self, TypeVar, overload

from ._api_types import _DEFAULT_SPACE, SaveFormat, SpaceName
from ._engine import Runtime, bridge, runtime
from .atoms import Atom
from .errors import Interrupted, PettaError
from .results import Rows
from .space import MeTTa
from .subscribe import SUBSCRIPTION_QUEUE_MAX
from .vocabularies import (
    AnswerPolicy,
    Atomicity,
    Fidelity,
    OnErrorMode,
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

    async def start(self) -> None:  # noqa: C901  -- start keeps the worker lifecycle state machine together so its branches share one state
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
            await started
            return

        def worker() -> None:  # noqa: C901  -- worker keeps the worker lifecycle state machine together so its branches share one state
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
                loop.call_soon_threadsafe(_set_future_result, started)
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
                            PettaError("AsyncMeTTa closed before this request ran"),
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

        self.thread = threading.Thread(target=worker, name="petta-aio", daemon=True)
        logger.debug("starting AsyncMeTTa worker thread")
        _remember_worker(self)
        try:
            self.thread.start()
        except BaseException as exc:
            _forget_worker(self)
            with self._state_lock:
                self._fail_locked(exc)
            raise
        await started

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
            raise PettaError(msg) from cause
        msg = f"AsyncMeTTa worker is {self._state}"
        raise PettaError(msg)

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
            failure = PettaError(
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
                "context(petta, interrupted))))",
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
                PettaError("AsyncMeTTa closed before this request ran"),
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
            raise PettaError(msg)
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
        PettaError,
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

        async with petta.aio.connect() as am:
            await am.add(S.edge(1, 2))
            rows = await am.query(S.edge(V.a, V.b))

    The exact rule should be: every finite request-response method forwards through the worker. Context managers, cursors, decorators, callback registrations, returned synchronous helper objects, and interactive entry points remain call() or synchronous-surface operations.

    call(fn) reaches anything not mirrored by running fn(m) on the engine's
    thread. interrupt() stops the evaluation the
    worker is running right now, and cancelling a waiting task (an
    asyncio timeout included) interrupts its own call, so the engine
    stops working for a listener that is gone.
    """

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self,
        space: str = _DEFAULT_SPACE,
        *,
        metta: MeTTa | None = None,
    ) -> None:
        self._m = metta if metta is not None else MeTTa(space)
        self._worker = _EngineThread()
        self._closed = False
        self._owner = True

    @classmethod
    def _sharing(cls, metta: MeTTa, worker: _EngineThread) -> AsyncMeTTa:
        shared = cls.__new__(cls)
        shared._m = metta
        shared._worker = worker
        shared._closed = False
        shared._owner = False
        return shared

    @property
    def space_name(self) -> SpaceName:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return self._m.space_name

    @property
    def metta(self) -> MeTTa:
        """The wrapped synchronous space, for engine-thread work via call()."""
        return self._m

    async def start(self) -> Self:
        """Start the engine thread; connect() and `async with` call this."""
        if self._closed:
            msg = "this AsyncMeTTa is closed"
            raise PettaError(msg)
        await self._worker.start()
        return self

    async def call(self, fn: Callable[[MeTTa], Any]) -> Any:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self._closed:
            msg = "this AsyncMeTTa is closed"
            raise PettaError(msg)
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
        reading). The stopped call raises petta.Interrupted; whatever it
        completed before the stop, writes included, stands. Callable from
        any thread or task.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._worker.interrupt_if_running(None)

    # ------------------------------------------------------- mirrored surface

    async def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[list[Atom]]:
        """Run MeTTa source on the worker and return its result groups."""
        return await self.call(
            lambda m: m.run(
                source,
                using,
                timeout=timeout,
                inferences=inferences,
            )
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

    async def save(self, path: str, format: SaveFormat = "metta") -> int:  # noqa: A002  -- format is the documented public save keyword and must remain compatible
        """Save this space and return the number of stored atoms."""
        return await self.call(lambda m: m.save(path, format=format))

    async def add(self, *atoms: Any) -> None:
        """Add atoms to this space on the worker."""
        return await self.call(lambda m: m.add(*atoms))

    async def add_table(self, head: Any, data: Any) -> int:
        """Add rows from a tabular value and return the number added."""
        return await self.call(lambda m: m.add_table(head, data))

    async def remove(self, atom: Any) -> bool:
        """Remove one matching atom and report whether one existed."""
        return await self.call(lambda m: m.remove(atom))

    async def clear(self) -> None:
        """Remove every atom from this space."""
        return await self.call(lambda m: m.clear())

    async def count(self) -> int:
        """Return the number of atoms in this space."""
        return await self.call(lambda m: m.count())

    async def atoms(self) -> list:
        """Return a snapshot of every atom in this space."""
        return await self.call(lambda m: m.atoms())

    async def query(
        self,
        *patterns: Any,
        where: Any | None = None,
        limit: int | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
        into: _builtins.type | None = None,
    ) -> Any:
        """Query patterns with the synchronous surface's bounds, guard,
        and into= row shaping.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return await self.call(
            lambda m: m.query(
                *patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
                into=into,
            )
        )

    async def eval(
        self,
        target: Any,
        *,
        using: dict[str, Any] | None = None,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list[Atom]:
        """Evaluate a term and return every answer."""
        return await self.call(
            lambda m: m.eval(
                target,
                using=using,
                timeout=timeout,
                inferences=inferences,
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
            lambda m: m.one(
                target,
                using=using,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def new_space(
        self,
        *,
        inherits: AsyncMeTTa | None = None,
        restricted: bool = False,
        grants: Sequence[str] = (),
    ) -> AsyncMeTTa:
        """Return an isolated space that borrows this connection's worker."""
        if inherits is not None and inherits._worker is not self._worker:
            msg = "an inherited async space must share this engine worker"
            raise ValueError(msg)
        parent = None if inherits is None else inherits._m
        requested_grants = tuple(grants)
        fresh = await self.call(
            lambda m: m.new_space(
                inherits=parent,
                restricted=restricted,
                grants=requested_grants,
            )
        )
        return AsyncMeTTa._sharing(fresh, self._worker)

    async def copy(self) -> AsyncMeTTa:
        """This space's contents in a new anonymous space; MeTTa.copy,
        the clone borrowing this connection's worker.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        clone = await self.call(lambda m: m.copy())
        return AsyncMeTTa._sharing(clone, self._worker)

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

    async def register_token(self, pattern: str, constructor: Callable[[str], Any]) -> None:
        """Register a full-lexeme reader class on the engine worker."""
        return await self.call(lambda m: m.register_token(pattern, constructor))

    async def unregister_token(self, pattern: str) -> None:
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

    unregister = unregister_op

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

    async def why(self, pattern: Any) -> str:
        """Explain why a pattern is not currently reducible."""
        return await self.call(lambda m: m.why(pattern))

    async def space(self, name: str) -> AsyncMeTTa:
        """Another space through the same engine thread. The connection
        owns the thread; spaces borrow it, so closing a borrowed space is
        a no-op and closing the owner ends them all.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        named = await self.call(lambda m: m.space(name))
        return AsyncMeTTa._sharing(named, self._worker)

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
            lambda m: m.first(
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
        """Install a library integration; see petta.integrate."""
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
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> list:
        """Evaluate and report each answer's outcome kind."""
        return await self.call(
            lambda m: m.eval_status(target, timeout=timeout, inferences=inferences)
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

    async def disassemble(self, name: str) -> str:
        """The Prolog clauses a function name compiled to."""
        return await self.call(lambda m: m.disassemble(name))

    async def declare_admits(self, name: str, type_name: str) -> Atom:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return await self.call(lambda m: m.declare_admits(name, type_name))

    async def declare_annotations(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        name: str,
        algebra: str,
        *,
        capabilities: Sequence[str] = (),
    ) -> Atom:
        return await self.call(
            lambda m: m.declare_annotations(
                name, algebra, capabilities=capabilities
            )
        )

    async def declare_algebra(
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
    ) -> Atom:
        """Declare one checked value algebra on the owning engine thread."""
        return await self.call(
            lambda m: m.declare_algebra(
                name,
                combine=combine,
                extend=extend,
                zero=zero,
                one=one,
                laws=laws,
                carrier=carrier,
                requires=requires,
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

    async def evaluate_algebra(
        self,
        query: str | Atom,
        *,
        algebra: str,
        max_rounds: int = 64,
    ) -> Any:
        """Evaluate the general tagged-rule form on the owning engine thread."""
        return await self.call(
            lambda m: m.evaluate_algebra(
                query, algebra=algebra, max_rounds=max_rounds
            )
        )

    async def sample_rates(
        self,
        query: str | Atom,
        *,
        algebra: str,
        draws: int,
        seed: int,
    ) -> tuple[Atom, ...]:
        """Draw from declared rates on the owning engine thread."""
        return await self.call(
            lambda m: m.sample_rates(
                query, algebra=algebra, draws=draws, seed=seed
            )
        )

    async def declare_capacity(self, name: str, limit: int) -> Atom:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return await self.call(lambda m: m.declare_capacity(name, limit))

    async def declare_context(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, name: str, world: World
    ) -> Atom:
        return await self.call(lambda m: m.declare_context(name, world))

    async def declare_emits(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, name: str, policy: AnswerPolicy
    ) -> Atom:
        return await self.call(lambda m: m.declare_emits(name, policy))

    async def declare_handles(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        name: str,
        pattern: str | Atom,
        fidelity: Fidelity,
        *,
        det: str | None = None,
    ) -> Atom:
        return await self.call(
            lambda m: m.declare_handles(name, pattern, fidelity, det=det)
        )

    async def declare_image(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        name: str,
        type_name: str,
        # policy-inventory-exempt: mechanism-internal; reason=the three modes by which one Python type crosses one context boundary, forwarded unchanged to the synchronous declaration door that owns them; evidence=bindings/python/petta/space.py:declare_image
        setting: Literal["opaque", "transparent", "auto"],
    ) -> Atom:
        return await self.call(
            lambda m: m.declare_image(name, type_name, setting)
        )

    async def declare_merge(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, pattern: str | Atom, policy: AnswerPolicy
    ) -> Atom:
        return await self.call(lambda m: m.declare_merge(pattern, policy))

    async def declare_on_error(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        name: str,
        pattern: str | Atom,
        mode: OnErrorMode,
    ) -> Atom:
        return await self.call(lambda m: m.declare_on_error(name, pattern, mode))

    async def declare_reaction(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, name: str, pattern: str | Atom, operation: str | Atom
    ) -> Atom:
        return await self.call(lambda m: m.declare_reaction(name, pattern, operation))

    async def declare_source(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, name: str, kind: SourceKind
    ) -> Atom:
        return await self.call(lambda m: m.declare_source(name, kind))

    async def declare_writes(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self,
        name: str,
        atomicity: Atomicity,
    ) -> Atom:
        return await self.call(lambda m: m.declare_writes(name, atomicity))

    async def register_op(
        self,
        fn: Callable,
        /,
        *,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=bindings/python/petta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Callable:
        """Register a Python callable as a MeTTa function. The engine
        calls it synchronously on the worker thread, exactly as the
        synchronous surface does; the decorator spelling stays with the
        synchronous surface, since decoration cannot await.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return await self.call(
            lambda m: m.register_op(
                fn,
                name=name,
                transport=transport,
                declarations=declarations,
                arities=arities,
                inverse=inverse,
            )
        )

    async def op(
        self,
        fn: Callable,
        /,
        *,
        name: str | None = None,
        # policy-inventory-exempt: mechanism-internal; reason=encoded and raw are the registration transport's two wire-crossing modes, decoded once into the (op ...) kind; evidence=bindings/python/petta/ops.py:_operation_kind
        transport: Literal["encoded", "raw"] = "encoded",
        declarations: Iterable[Atom] = (),
        arities: list[int] | None = None,
        inverse: Callable | None = None,
    ) -> Callable:
        """register_op under its short name."""
        return await self.call(
            lambda m: m.op(
                fn,
                name=name,
                transport=transport,
                declarations=declarations,
                arities=arities,
                inverse=inverse,
            )
        )

    async def define(
        self,
        fn: Callable | None = None,
        /,
        *,
        prolog: str | os.PathLike[str] | None = None,
    ) -> Any:
        """Compile a Python function into equations on the worker. The
        returned handle's own calls are synchronous doors; evaluate
        through fn(name) or run() from async code.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if fn is not None:
            return await self.call(lambda m: m.define(fn))
        if prolog is None:
            msg = "define takes a function or prolog= source"
            raise TypeError(msg)
        source = prolog
        return await self.call(lambda m: m.define(prolog=source))

    async def type(
        self,
        cls: _builtins.type,
        /,
        *,
        accessors: bool = True,
        methods: bool = True,
    ) -> _builtins.type:
        """Declare a Python class into this space. A call, not a
        decorator: decoration cannot await.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return await self.call(
            lambda m: m.type(cls, accessors=accessors, methods=methods)
        )

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

    async def register_space(self, provider: Any, name: str) -> Any:
        """Register a Python-backed space. Its methods run on whichever
        thread the engine is answering from, exactly as in sync use.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return await self.call(lambda m: m.register_space(provider, name))

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

    async def unregister_space(self, name: str) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        return await self.call(lambda m: m.unregister_space(name))

    def limits(
        self,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ):
        """Scoped default bounds, the synchronous surface's own block:
        enter and exit only touch a contextvar, so this is an ordinary
        `with` inside async code, and every awaited call in the scope
        carries it to the worker.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return self._m.limits(timeout=timeout, inferences=inferences)

    def capture(self):
        """Collect awaited run/eval output in an ordinary task-local scope."""
        return self._m.capture()

    def atomic(self):
        """Make each awaited run in the block one engine transaction."""
        return self._m.atomic()

    def speculative(self):
        """Answer awaited runs while discarding their engine writes."""
        return self._m.speculative()

    def strict(self):
        """Refuse unreduced directives in awaited runs within the block."""
        return self._m.strict()

    def batch(self) -> _AsyncBatch:
        """Collect this space's add() calls and cross once at exit,
        the synchronous batch's async twin: `async with am.batch():`.
        The same stated edges apply: reads see the pre-batch space,
        remove and clear refuse, an exception discards.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncBatch(self)

    async def transaction(self, fn: Callable[[MeTTa], Any], /) -> Any:
        """Run fn inside one engine transaction on the worker thread,
        answering its return value. fn receives the worker's own
        synchronous MeTTa, because a transaction body is a closed
        synchronous goal (SWI's transaction/1 takes one), which is also
        why there is no async body and no transactional decorator here.
        A raise rolls every engine write back and re-raises as itself.

            await am.transaction(lambda m: m.add(S.fact(1)))
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return await self.call(lambda m: m.transaction(lambda: fn(m)))

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
            await am.query(...)
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
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> _AsyncCursor:
        """query(), pulled asynchronously: one row per worker round trip.

            async with am.stream(S.edge(V.a, V.b)) as rows:
                async for row in rows:
                    ...

        Iterating without the async-with also works; aclose() is then the
        caller's duty, the finalization reading the data model gives
        asynchronous iterators.
        """
        return _AsyncCursor(self, patterns, where, timeout, inferences)

    def subscribe(
        self, pattern: Any, *, on: str = "add", queue_max: int = SUBSCRIPTION_QUEUE_MAX
    ) -> _AsyncSubscription:
        """A standing query as an async event stream: every matching
        write becomes an Event on an asyncio queue, consumed with
        async-for. The synchronous surface's callback form stays there;
        here the stream IS the delivery.

            async with am.subscribe(S.order(V.id), on="add") as events:
                async for event in events:
                    ...
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncSubscription(self, pattern, on, queue_max)

    def fn(self, name: str) -> _AsyncEngineFunction:
        """An engine function as an async callable: await f(3), with
        .one, .first and .all carrying the same cardinality triple.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _AsyncEngineFunction(self, name)

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
        return f"AsyncMeTTa({self._m.space_name!r}, {state})"


_EXHAUSTED: Final = object()
_STREAM_CLOSED: Final = object()


class _AsyncStats:
    """MeTTa.stats() as an async context manager: the counters start and
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
        self._cm = await self._am.call(lambda m: m.assuming(*facts))
        cm = self._cm
        await self._am.call(lambda _m: cm.__enter__())
        return self._am

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
        return f"<async prepared query {self.columns} on {self._am.space_name}>"


class _AsyncCursor:
    """MeTTa.stream() pulled asynchronously: one row per worker round
    trip, closable, and an async context manager. Iterating without the
    async-with works too; aclose() is then the caller's duty, the
    finalization reading the data model gives asynchronous iterators.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am, patterns, where, timeout, inferences) -> None:
        self._am = am
        self._patterns = patterns
        self._where = where
        self._timeout = timeout
        self._inferences = inferences
        self._cursor: Any = None
        self._closed = False

    async def _ensure(self) -> Any:
        if self._cursor is None:
            patterns, where = self._patterns, self._where
            timeout, inferences = self._timeout, self._inferences
            self._cursor = await self._am.call(
                lambda m: m.stream(
                    *patterns, where=where, timeout=timeout, inferences=inferences
                )
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
        if self._closed:
            return
        self._closed = True
        if self._cursor is not None:
            cursor = self._cursor
            await self._am.call(lambda _m: cursor.close())

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
    ) -> None:
        self._am = am
        self._pattern = pattern
        self._on = on
        self._queue_max = queue_max
        self._subscription: Any = None
        self._queue: asyncio.Queue[Any] | None = None
        self._closed = False
        self._dropped = 0

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

    async def _ensure(self) -> asyncio.Queue[Any]:
        if self._queue is None:
            loop = asyncio.get_running_loop()
            events: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._queue_max)
            self._queue = events

            def deliver(event: Any) -> None:
                loop.call_soon_threadsafe(self._offer, events, event)

            pattern, on = self._pattern, self._on
            self._subscription = await self._am.call(
                lambda m: m.subscribe(pattern, deliver, on=on)
            )
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
            raise PettaError(
                msg
            )
        event = await events.get()
        if event is _STREAM_CLOSED:
            raise StopAsyncIteration
        return event

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._subscription is not None:
            subscription = self._subscription
            await self._am.call(lambda _m: subscription.cancel())
        if self._queue is not None:
            self._queue.put_nowait(_STREAM_CLOSED)

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


class _AsyncEngineFunction:
    """One engine function as an async callable, the cardinality triple
    spelled the same as everywhere: await f(3) is one(), .first
    tolerates absence, .all answers the multiset.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, am: AsyncMeTTa, name: str) -> None:
        self._am = am
        self._name = name
        self.__name__ = name
        self.__qualname__ = f"{am.space_name}.{name}"

    async def __call__(self, *args: Any) -> Any:
        return await self.one(*args)

    async def one(self, *args: Any) -> Any:
        name = self._name
        return await self._am.call(lambda m: m.fn(name).one(*args))

    async def first(self, *args: Any) -> Any:
        name = self._name
        return await self._am.call(lambda m: m.fn(name).first(*args))

    async def all(self, *args: Any) -> list:
        name = self._name
        return await self._am.call(lambda m: m.fn(name).all(*args))

    def __repr__(self) -> str:
        return f"<async engine function {self._name} on {self._am.space_name}>"


async def connect(
    space: str = _DEFAULT_SPACE,
    *,
    metta: MeTTa | None = None,
) -> AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return await AsyncMeTTa(space, metta=metta).start()
