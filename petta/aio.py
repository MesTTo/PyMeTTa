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
  Future Enhancements: None
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import math
import queue
import threading
import warnings
import weakref
from collections.abc import Callable
from typing import Any, Self

from ._engine import bridge, runtime
from .errors import Interrupted, PettaError
from .results import Rows
from .space import MeTTa

logger = logging.getLogger(__name__)

__all__ = ["AsyncMeTTa", "connect"]

DEFAULT_CLOSE_TIMEOUT = 10.0
_LIVE_WORKERS: weakref.WeakSet[_EngineThread] = weakref.WeakSet()
_LIVE_WORKERS_LOCK = threading.Lock()


def _set_future_exception(future: asyncio.Future[None], failure: BaseException) -> None:
    if not future.done():
        future.set_exception(failure)


def _set_future_result(future: asyncio.Future[None]) -> None:
    if not future.done():
        future.set_result(None)


class _Request:
    __slots__ = ("abandoned", "fn", "future", "loop", "target")

    def __init__(self, fn, target, loop, future) -> None:
        self.fn = fn
        self.target = target
        self.loop = loop
        self.future = future
        self.abandoned = threading.Event()


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
    """

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
                    raise RuntimeError("starting AsyncMeTTa has no startup future")
                launch = False
            elif self._state in ("failed", "closing", "closed"):
                self._raise_state_locked()
            else:
                started = loop.create_future()
                self._startup = started
                self._state = "starting"
                launch = True

        if started is None:
            raise RuntimeError("AsyncMeTTa startup did not create a future")
        if not launch:
            await started
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
                        result = request.fn(request.target)
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
            raise PettaError(f"AsyncMeTTa worker failed{detail}") from cause
        raise PettaError(f"AsyncMeTTa worker is {self._state}")

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
        signal was sent."""
        with self._state_lock:
            swi_thread = self._swi_thread
        with self._transition:
            current = self._current
            if current is None or (request is not None and current is not request):
                return False
            if swi_thread is None:
                raise RuntimeError(
                    "the async worker has a request but no published Prolog engine"
                )
            # query_once is safe from a bare foreign thread (the loop's),
            # and this bypasses the runtime lock on purpose: the running
            # goal holds that lock, and the signal is how it lets go.
            bridge().query_once(
                "thread_signal(T, throw(error(petta_py_exception(interrupted, none), "
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
            raise PettaError("an AsyncMeTTa worker cannot stop itself")
        self.interrupt_if_running(None)
        thread.join(timeout)
        if thread.is_alive():
            self.interrupt_if_running(None)
            logger.error("AsyncMeTTa worker exceeded its stop timeout")
            raise TimeoutError(
                f"AsyncMeTTa worker did not stop within {timeout:g} seconds"
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
        raise ValueError(f"close timeout must be finite and positive, got {timeout!r}")
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
    if workers:
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
        raise ExceptionGroup(
            f"failed to stop {len(failures)} AsyncMeTTa worker(s) at exit",
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

    def __init__(self, space: str = "&self", *, metta: MeTTa | None = None) -> None:
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
    def space_name(self) -> str:
        return self._m.space_name

    @property
    def metta(self) -> MeTTa:
        """The wrapped synchronous space, for engine-thread work via call()."""
        return self._m

    async def start(self) -> Self:
        """Start the engine thread; connect() and `async with` call this."""
        if self._closed:
            raise PettaError("this AsyncMeTTa is closed")
        await self._worker.start()
        return self

    async def call(self, fn: Callable[[MeTTa], Any]) -> Any:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all."""
        if self._closed:
            raise PettaError("this AsyncMeTTa is closed")
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
        any thread or task."""
        return self._worker.interrupt_if_running(None)

    # ------------------------------------------------------- mirrored surface

    async def run(
        self,
        source: str,
        using: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool = False,
        atomic: bool = False,
        speculative: bool = False,
    ) -> Any:
        """Run MeTTa source on the worker and return its result groups."""
        return await self.call(
            lambda m: m.run(
                source,
                using,
                timeout=timeout,
                inferences=inferences,
                capture=capture,
                atomic=atomic,
                speculative=speculative,
            )
        )

    async def load(self, path: str) -> list:
        """Load source or a fast cache into this space on the worker."""
        return await self.call(lambda m: m.load(path))

    async def save(self, path: str, format: str = "metta") -> int:
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
    ) -> Rows:
        """Query patterns with the synchronous surface's bounds and guard."""
        return await self.call(
            lambda m: m.query(
                *patterns,
                where=where,
                limit=limit,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def eval(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
        capture: bool = False,
        residuals: bool = False,
    ) -> Any:
        """Evaluate a term and return every answer."""
        return await self.call(
            lambda m: m.eval(
                target,
                timeout=timeout,
                inferences=inferences,
                capture=capture,
                residuals=residuals,
            )
        )

    async def value(
        self,
        target: Any,
        *,
        timeout: float | None = None,
        inferences: int | None = None,
    ) -> Any:
        """Evaluate a term that must produce exactly one value."""
        return await self.call(
            lambda m: m.value(
                target,
                timeout=timeout,
                inferences=inferences,
            )
        )

    async def fresh_space(self) -> AsyncMeTTa:
        """Return an isolated space that borrows this connection's worker."""
        fresh = await self.call(lambda m: m.fresh_space())
        return AsyncMeTTa._sharing(fresh, self._worker)

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

    async def cast(self, value: Any, type_: Any) -> Any:
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
        a no-op and closing the owner ends them all."""
        named = await self.call(lambda m: m.space(name))
        return AsyncMeTTa._sharing(named, self._worker)

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
                raise TimeoutError(
                    f"AsyncMeTTa worker did not stop within {timeout:g} seconds"
                )

    def stop(self, timeout: float = DEFAULT_CLOSE_TIMEOUT) -> None:
        """Synchronous cleanup for code without a running event loop."""
        self._closed = True
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
        return f"AsyncMeTTa({self._m.space_name!r}, {state})"


async def connect(space: str = "&self", *, metta: MeTTa | None = None) -> AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point."""
    return await AsyncMeTTa(space, metta=metta).start()
