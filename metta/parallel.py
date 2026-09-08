"""Purpose: evaluate on more than one core, at either boundary. An EnginePool
owns a fixed set of worker THREADS, each holding its own attached Prolog
engine for the pool's lifetime, and runs ordinary Python callables on them;
because a worker's engine is private to its thread, the process lock that
serialises the home engine does not apply to it, so the branches genuinely
run at once. A ProcessPool owns worker PROCESSES that each boot an engine of
their own and share nothing, for when isolation is the point.

Both are concurrent.futures.Executor, so `submit`, `map`, `shutdown`, `with`,
`as_completed` and `wait` are Python's own words on them, and both take their
fan-out doors from one _FanOut mixin so the two boundaries answer alike.

This is the Python-side fan-out. Space.parallel() is the in-engine fan-out
through hyperpose, below a single janus call. They compose: a pool worker may
itself evaluate a hyperpose.

    with metta.parallel.pool(workers=8) as p:
        answers = list(p.map(lambda n: m.eval(S.solve(n))[0], range(64)))

    with metta.parallel.process_pool(4, boot=rules) as p:
        answers = list(p.map(metta.parallel.program, programs))

Assumes:
  - metta._engine.engine_thread attaches an engine to a bare foreign thread
    and detaches exactly the engine it attached [tested
    test_engine_thread_owns_only_its_attachment]
  - MeTTa's shared Prolog structures carry their own mutexes, so concurrent
    engines do not corrupt them: '$metta_specializer' in specializer.pl,
    '$metta_native_storage' in spaces.pl, metta_loader around
    process_metta_string in filereader.pl, and a per-function mutex in
    lib_memo.pl [source 2026-08-15]
Guarantees:
  - a waiting close joins owned workers after nonwaiting close or join failure
    [tested: test_waiting_close_joins_after_nonwaiting_close; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
  - package coordination functions evaluate lib_thread in the ambient space;
    spawned and repeating computations stay Space handles whose answers may
    be iterated as they arrive [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a worker engine answers exactly what the home engine answers
    [tested test_pool_agrees_with_the_home_engine]
  - map answers in input order however the workers finish
    [tested test_map_answers_in_input_order]
  - both pools ARE Executors: submit/map/shutdown/with are Python's own, and
    as_completed reads their Futures [tested:
    test_the_pool_is_an_executor_python_recognises,
    test_as_completed_yields_every_future; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - shutdown(cancel_futures=True) cancels what is queued and leaves what a
    worker started [tested: test_shutdown_cancels_queued_futures;
    commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a process worker boots its own engine once and answers what the parent
    answers for the same program [tested:
    test_the_process_pool_runs_three_programs_in_three_workers,
    test_a_process_pool_answers_what_the_sequential_run_answers;
    commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a call reaching an engine handle refuses at submit rather than opening a
    different space in the worker [tested:
    test_a_closure_over_a_space_refuses_at_submit,
    test_a_module_global_space_refuses_at_submit; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a handle refuses to cross a process boundary in either direction
    [tested: test_a_space_answer_refuses_to_cross; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
  - a worker exception is raised to the caller rather than swallowed: one
    plainly, several together as one ExceptionGroup in input order
    [tested test_map_raises_every_failure_in_input_order]
  - branches really run at once [tested:
    extensions/python/tests/ch14_seeing_your_program/test_engine_pool.py::test_pool_runs_work_concurrently;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - every worker releases its engine on close, including after an exception
    [tested test_close_releases_every_engine]
  - every Python and engine-backed spawn call snapshots ContextVars at launch,
    including EnginePool's OS-thread jobs [tested:
    test_context_snapshot_crosses_every_spawn_door_including_thread_workers;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - pool submission is linearized with close, so every accepted Future reaches
    a worker before its stop sentinel; a closed pool refuses new work naming
    the cause rather than hanging [tested:
    test_submit_and_close_linearize_accepted_work,
    test_closed_pool_refuses_work; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - FutureSpace iteration performs a terminal drain after settlement and cannot
    lose an answer inserted between its live snapshot and settled check [tested:
    test_future_iteration_drains_the_terminal_snapshot; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - FutureSpace reads its initial bag and terminal reconciliation once, then
    consumes additions by publication position; P quiet waits over N answers
    cost theta(P+N), and equal answers on either side of the snapshot remain
    distinct occurrences [tested:
    test_future_iteration_does_not_resnapshot_per_quiet_wait,
    test_future_iteration_watermark_separates_snapshot_from_later_events;
    commit=1877bec75a9a22265c9222f0c0c538c8f65a983f]
  - an abandoned Channel destroys its SWI message queue from whichever thread
    collects the Python handle [tested:
    test_abandoned_channels_destroy_their_swi_queues_from_collector_thread;
    commit=8909645dc7b390e4c6e7af77bfc75791c4f0aea1]
Fails when:
  - the work is not engine-bound. A pool costs one thread and one engine per
    worker, so fanning out calls that are already fast buys queueing overhead
    and nothing else.
  - the callables mutate shared Python state. The pool serialises nothing on
    the Python side; that is the caller's problem, as with any thread pool.
Owns:
  - one daemon thread and one attached Prolog engine per worker, from start
    until close(). close() is idempotent and runs from __exit__.
  - one process, one booted engine and one boot program per ProcessPool
    worker, from the first submit until shutdown(), plus the SimpleQueue
    carrying those workers' boot timings.
  - one SWI message queue per Channel, released by close(), context exit, or a
    finalizer that retains only the runtime and engine handle.
Guarded by:
  - _state_lock publishes the pool's state and worker list; the work queue is
    a queue.Queue and needs no further locking.
Decides:
  - workers defaults to os.cpu_count(), the same default library(thread)'s
    jobs/2 uses for concurrent_and/3.
  - the process pool lives HERE rather than behind a lazy submodule: given
    this module's own imports, concurrent.futures.process adds 3.5ms and
    14.7M instructions, +2.7% of importing metta.parallel, which is a
    smaller price than a second module name for one class
    [measured 2026-09-07: 545.7M against 560.4M instructions:u, minimum of
    three; command=perf stat -e instructions:u python -c "import
    metta.parallel[, concurrent.futures.process]"; fixture=this checkout
    under load 44; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb].
  - a fan-out door answers an ITERATOR over results that already exist, not
    a list: the whole input is submitted and taken before the door returns,
    which is what these pools have always done, while the type is
    Executor.map's own so the class is one rather than resembling one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import contextvars
import functools
import inspect
import logging
import multiprocessing
import os
import queue
import sys
import threading
import time
import weakref as _weakref
from collections import Counter, deque
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import Executor, Future, ProcessPoolExecutor, as_completed
from itertools import batched
from types import FunctionType, MethodType
from typing import Any, Self, override

from ._engine import Runtime, engine_thread, forked, runtime
from ._space import MeTTa, Space
from .atoms import (
    Atom,
    Expression,
    Handle,
    Symbol,
    Undefined,
    Variable,
    _atom_from_wire,
    _to_atom,
)
from .errors import MettaError, Timeout
from .vocabularies import SubscriptionEdge

logger = logging.getLogger(__name__)


__all__ = [
    "Channel",
    "EnginePool",
    "FutureSpace",
    "ProcessPool",
    "call",
    "channel",
    "every",
    "par_map",
    "pool",
    "process_pool",
    "program",
    "race",
    "spawn",
]

# What a worker takes off the queue: the future to settle, and the call.
_Job = tuple[
    "Future[Any]",
    contextvars.Context,
    Callable[..., Any],
    tuple[Any, ...],
    dict[str, Any],
]


def _apply_chunk[R](fn: Callable[..., R], rows: Sequence[tuple[Any, ...]]) -> list[R]:
    """Run one chunk of calls in order: the unit every fan-out door submits.

    A module-level function rather than a closure, because a process pool
    pickles what it submits BY REFERENCE and a closure has no reference to
    pickle. CPython's own ProcessPoolExecutor batches through the same shape
    [source: Lib/concurrent/futures/process.py, _process_chunk; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb].
    """
    return [fn(*row) for row in rows]


def _raise_failures(failures: list[BaseException], tasks: int) -> None:
    """The library's raise_for_errors policy over one fan-out's failures.

    One failure raises plainly; several raise together as one group in INPUT
    order, so what a caller sees never depends on which worker lost the race
    and no failure after the first goes unreported. BaseExceptionGroup picks
    the Exception-only subclass itself when every leaf is an Exception.
    """
    if len(failures) == 1:
        raise failures[0]
    if failures:
        msg = f"{len(failures)} of {tasks} pool tasks failed"
        raise BaseExceptionGroup(msg, failures)


class _FanOut(Executor):
    """map, starmap and imap_unordered over whatever submit() a pool has.

    Both pools in this module fan work out identically and differ only in
    where the work lands, so the three doors are written once here and each
    pool supplies `submit`. That also makes them faces of
    concurrent.futures.Executor rather than lookalikes: `as_completed`,
    `wait`, `with` and `map` are Python's own words on both.

    ONE RULE FOR ALL THREE: every door SUBMITS the whole input before it
    answers, and answers an iterator over results that already exist. That
    is the pools' established contract ("the whole point is that the work
    already ran") and it is why `map` here raises at the call rather than at
    the first `next()`. Executor.map is lazy in RETRIEVAL, and the two agree
    on everything a `for` loop can see; where they differ is a map written
    for its side effects, which a lazy map silently never runs. Choosing
    laziness would have made that a silent no-op, which this library does
    not ship [tested: test_a_worker_can_write_and_the_home_engine_sees_it;
    commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb].
    """

    @override
    def map[R](
        self,
        fn: Callable[..., R],
        *iterables: Iterable[Any],
        timeout: float | None = None,
        chunksize: int = 1,
        buffersize: int | None = None,
    ) -> Iterator[R]:
        """Run fn across the workers over zipped iterables, in input order.

        Executor.map's signature exactly, with Executor.map's meaning for
        every keyword: `timeout` is a deadline for the whole fan-out and
        raises Timeout, `chunksize` groups items into one submitted task,
        and `buffersize` bounds how many submitted tasks may be waiting for
        their result to be taken.

        `chunksize` is HONOURED here rather than ignored (ThreadPoolExecutor
        ignores it), because a chunk is a real unit in both pools: it
        amortises queueing in the thread pool and one pickle round trip in
        the process pool. A chunk is also one failure unit, so the default 1
        is what gives per-item grouping.

        Answers arrive in input order however the workers finish, one
        failure raises plainly, and several raise together as one
        ExceptionGroup in input order; the remaining work is left to finish
        rather than half-cancelled, except after a `timeout`, which cancels
        what has not started.
        """
        return self._fan_out(fn, zip(*iterables, strict=False), timeout, chunksize, buffersize)

    def starmap[R](
        self,
        fn: Callable[..., R],
        rows: Iterable[Iterable[Any]],
        *,
        timeout: float | None = None,
        chunksize: int = 1,
        buffersize: int | None = None,
    ) -> Iterator[R]:
        """map() for a callable of several arguments, spelled as itertools does.

        The same door as `map` reading its input the other way up: `map`
        takes one iterable per ARGUMENT and zips them, `starmap` takes one
        row per CALL and spreads it. Everything else, order, failures,
        `timeout`, `chunksize` and `buffersize`, is `map`'s.
        """
        return self._fan_out(
            fn, (tuple(row) for row in rows), timeout, chunksize, buffersize
        )

    def close(self, wait: bool = True) -> None:  # noqa: FBT001, FBT002  -- the boolean is established API data and positional compatibility is part of the call shape
        """Stop accepting work and release every engine after queued work finishes.

        The pools' own name for `shutdown(wait=)`, kept because it is the
        name this door has always had and the one every `with` block leaves
        through. `shutdown` is the same teardown with Executor's
        `cancel_futures` beside it.
        """
        self.shutdown(wait=wait)

    def imap_unordered[T, R](self, fn: Callable[[T], R], items: Iterable[T]) -> Iterator[R]:
        """Yield results as they finish rather than in input order.

        `map`'s completion-order face, and the longhand it is sugar for is
        `as_completed(pool.submit(fn, item) for item in items)`. Use it when
        the caller can start consuming before the slowest item lands; `map`
        is the right default because input order is what almost every caller
        means. A failure raises at the position it is reached, so this door
        does not group: it has no input order to group in.
        """
        futures = [self.submit(fn, item) for item in items]
        for future in as_completed(futures):
            yield future.result()

    def _fan_out[R](
        self,
        fn: Callable[..., R],
        rows: Iterator[tuple[Any, ...]],
        timeout: float | None,
        chunksize: int,
        buffersize: int | None,
    ) -> Iterator[R]:
        """Submit every chunk, take every result, then answer them in order."""
        if isinstance(chunksize, bool) or not isinstance(chunksize, int):
            msg = f"chunksize must be an integer, not {type(chunksize).__name__}"
            raise TypeError(msg)
        if chunksize < 1:
            msg = f"chunksize must be > 0, not {chunksize}"
            raise ValueError(msg)
        if buffersize is not None:
            if isinstance(buffersize, bool) or not isinstance(buffersize, int):
                msg = "buffersize must be an integer or None"
                raise TypeError(msg)
            if buffersize < 1:
                msg = "buffersize must be None or > 0"
                raise ValueError(msg)
        deadline = None if timeout is None else time.monotonic() + timeout
        pending: deque[Future[list[R]]] = deque()
        results: list[R] = []
        failures: list[BaseException] = []
        tasks = 0
        for chunk in batched(rows, chunksize):
            pending.append(self.submit(_apply_chunk, fn, chunk))
            tasks += 1
            if buffersize is not None and len(pending) >= buffersize:
                self._take(pending, results, failures, deadline, timeout)
        while pending:
            self._take(pending, results, failures, deadline, timeout)
        _raise_failures(failures, tasks)
        return iter(results)

    def _take[R](
        self,
        pending: deque[Future[list[R]]],
        results: list[R],
        failures: list[BaseException],
        deadline: float | None,
        timeout: float | None,
    ) -> None:
        """Fold the oldest submitted chunk in, or end the fan-out on its deadline.

        The loop finishes even after a failure, and that is the point rather
        than tidiness: a Future whose result is never fetched drops its
        exception without a word, so leaving the rest undrained would lose
        every failure after the first.

        BaseException is caught deliberately. A worker's KeyboardInterrupt
        has to reach the caller, grouped if it arrived beside other
        failures, and filtering it out for not being an Exception is exactly
        how an interrupt gets swallowed.

        A TimeoutError is the one exception this has to read twice, because
        metta.errors.Timeout IS a builtin TimeoutError and a callable may
        raise one of its own. `future.done()` separates them exactly: a
        finished future raised the callable's, an unfinished one lost the
        wait.
        """
        future = pending.popleft()
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        try:
            results.extend(future.result(remaining))
        except TimeoutError as exc:
            if future.done():
                failures.append(exc)
                return
            future.cancel()
            for other in pending:
                other.cancel()
            pending.clear()
            msg = f"the pool did not finish this map within {timeout} seconds"
            failures.append(Timeout(msg))
        except BaseException as exc:  # noqa: BLE001
            failures.append(exc)


class EnginePool(_FanOut):
    """Worker threads that each hold their own Prolog engine.

    Construct through pool() or MeTTa.pool(). The pool starts its workers
    eagerly, so that a first map() does not pay engine attachment, and holds
    them until close(): attaching and detaching an engine is documented as
    relatively expensive (SWI manual section 10.6.1).

    It IS a concurrent.futures.Executor, so `submit`, `map`, `shutdown` and
    `with` are Python's own words on it and `as_completed(futures)` and
    `wait(futures)` read its Futures without knowing what a MeTTa engine is.
    `close(wait=)` is the same door as `shutdown(wait=)` under the name this
    pool has always had; `shutdown` adds Executor's `cancel_futures`. The
    fan-out doors come from _FanOut, which states their one shared rule.
    """

    def __init__(self, workers: int | None = None) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        if workers is None:
            workers = os.cpu_count() or 1
        if not isinstance(workers, int) or isinstance(workers, bool):
            msg = f"workers must be an int, not {type(workers).__name__}"
            raise TypeError(msg)
        if workers < 1:
            msg = f"a pool needs at least one worker, not {workers}"
            raise ValueError(msg)

        # Start the runtime HERE rather than in a worker: consulting is
        # serialised behind CONSULT_LOCK anyway, and doing it on the caller's
        # thread means a startup failure raises from the constructor instead
        # of being delivered through a worker that then has no engine.
        runtime()

        self._workers = workers
        self._work: queue.Queue[_Job | None] = queue.Queue()
        self._state_lock = threading.Lock()
        self._closed = False
        self._started: list[threading.Thread] = []
        self._ready = threading.Barrier(workers + 1, timeout=60)
        self._start_error: BaseException | None = None
        self._start()

    # ------------------------------------------------------------------ startup

    def _start(self) -> None:
        for index in range(self._workers):
            thread = threading.Thread(
                target=self._worker,
                name=f"metta-pool-{index}",
                daemon=True,
            )
            thread.start()
            self._started.append(thread)
        try:
            self._ready.wait()
        except threading.BrokenBarrierError as exc:
            self.close()
            msg = "a pool worker could not attach its Prolog engine"
            raise MettaError(
                msg
            ) from self._start_error or exc
        if self._start_error is not None:
            failure = self._start_error
            self.close()
            msg = "a pool worker could not attach its Prolog engine"
            raise MettaError(msg) from failure

    def _worker(self) -> None:
        """Attach one engine, then serve the queue until the stop sentinel.

        engine_thread() owns the attachment, so the engine is released on
        every exit path including an exception escaping the loop.
        """
        try:
            with engine_thread():
                try:
                    self._ready.wait()
                except threading.BrokenBarrierError:
                    return
                self._serve()
        except BaseException as exc:
            # Record the first failure and break the barrier, so a constructor
            # waiting on it raises instead of blocking for the full timeout.
            with self._state_lock:
                if self._start_error is None:
                    self._start_error = exc
            self._ready.abort()
            logger.exception("a metta pool worker stopped")

    def _serve(self) -> None:
        while True:
            job = self._work.get()
            if job is None:
                return
            future, context, fn, args, kwargs = job
            if not future.set_running_or_notify_cancel():
                continue
            try:
                result = context.run(fn, *args, **kwargs)
            except BaseException as exc:  # noqa: BLE001
                # A BaseException crosses to the caller too: a worker that
                # swallowed KeyboardInterrupt would hide it entirely.
                future.set_exception(exc)
            else:
                future.set_result(result)

    # -------------------------------------------------------------------- submit

    @override
    def submit[R](self, fn: Callable[..., R], /, *args: Any, **kwargs: Any) -> Future[R]:
        """Queue one call on a worker and answer its Future."""
        with self._state_lock:
            if self._closed:
                msg = (
                    "this pool is closed and cannot take new work; "
                    "build another with metta.parallel.pool()"
                )
                raise MettaError(
                    msg
                )
            # ThreadPoolExecutor uses the same transition: accepting work and
            # inserting it precede shutdown's sentinel under one state lock.
            future: Future[R] = Future()
            self._work.put((future, contextvars.copy_context(), fn, args, kwargs))
        return future

    # --------------------------------------------------------------- lifecycle

    @override
    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Executor's teardown: stop taking work, then release every engine.

        wait=False returns while the owned workers drain. A later waiting
        shutdown still joins them, including after an earlier join timed
        out. Cancelling a Future skips only that queued task, not worker
        teardown.

        cancel_futures=True cancels every task still QUEUED, leaving what a
        worker already started to finish; that is ThreadPoolExecutor's own
        reading, and it drains the queue under the same state lock that
        submit takes, so a task accepted after the drain cannot exist.
        """
        with self._state_lock:
            first = not self._closed
            self._closed = True
            if cancel_futures:
                # The drain removes stop sentinels along with the work, so
                # the sentinels are re-queued below rather than assumed.
                while True:
                    try:
                        job = self._work.get_nowait()
                    except queue.Empty:
                        break
                    if job is not None:
                        job[0].cancel()
            if first or cancel_futures:
                for _ in self._started:
                    self._work.put(None)
        if not wait:
            return
        if threading.current_thread() in self._started:
            msg = "a pool worker cannot join itself; use close(wait=False)"
            raise MettaError(msg)
        for thread in self._started:
            thread.join(timeout=30)
        still_running = [t.name for t in self._started if t.is_alive()]
        if still_running:
            msg = f"pool workers did not stop within 30s: {', '.join(still_running)}"
            raise MettaError(
                msg
            )

    @property
    def workers(self) -> int:
        """How many worker threads, and therefore engines, this pool holds."""
        return self._workers

    @property
    def closed(self) -> bool:
        """Whether close() has run."""
        return self._closed

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.shutdown(wait=True)

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self._workers

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        state = "closed" if self._closed else "live"
        return f"<EnginePool workers={self._workers} {state}>"


def pool(workers: int | None = None) -> EnginePool:
    """A pool of worker threads that each hold their own Prolog engine.

    Use it as a context manager so the engines are released:

        with metta.parallel.pool(workers=4) as p:
            answers = list(p.map(lambda n: m.eval(S.fib(n))[0], range(20)))

    workers defaults to os.cpu_count().
    """
    return EnginePool(workers)


def imap_unordered[T, R](
    engine_pool: _FanOut, fn: Callable[[T], R], items: Iterable[T]
) -> Iterator[R]:
    """`pool.imap_unordered(fn, items)` written with the pool in front.

    The same door as the method, kept because it is the spelling this
    module has always published and because it reads as a free function
    over any pool. Either pool answers it.
    """
    return engine_pool.imap_unordered(fn, items)


# ------------------------------------------------- one engine per PROCESS

#: What a worker's boot left behind when it failed, read by the work units
#: below so a broken boot names itself instead of breaking the pool silently.
#: One per worker process, written once before that worker takes any work.
_WORKER_BOOT_FAILURE: BaseException | None = None

#: How far into a submitted call the process pool looks for an engine handle:
#: the callable itself, and one callable found inside it or beside it. Two
#: hops reach the shape `map` submits, `_apply_chunk(user_fn, rows)`, and its
#: user_fn's own closure. Deeper than that the walk would be reading a
#: program's whole object graph on every submit.
_CALLABLE_HOPS = 2

#: Handles on live engine state in THIS process. None of them means anything
#: in another one, and Space is the dangerous member: it PICKLES, by name.
_ENGINE_HANDLES: tuple[type, ...] = (Space, MeTTa, Runtime, EnginePool)


def _start_method() -> str:
    """The start method: forkserver where it exists, spawn elsewhere, never fork.

    Python 3.14 made forkserver the default start method on Linux for this
    class of hazard [source:
    https://docs.python.org/3.14/library/multiprocessing.html#contexts-and-start-methods].
    It is preferred over spawn where both exist because its server process
    is forked once, from an image that booted no engine, so each worker
    starts clean without paying a whole interpreter start.
    """
    if sys.platform == "linux" and "forkserver" in multiprocessing.get_all_start_methods():
        return "forkserver"
    return "spawn"


def _work_space(space: Symbol | str | None) -> Space:
    """The space a work unit runs in, named rather than handed over."""
    if space is None:
        return _ambient_space()
    if isinstance(space, Space):
        msg = (
            "a work unit names its space, it does not carry one: a Space "
            "handle belongs to the process that opened it. Pass the name, "
            "space=S.kb or space='&kb'."
        )
        raise TypeError(msg)
    if not isinstance(space, Symbol | str):
        msg = (
            f"a work unit names its space by symbol or by exact string, not "
            f"{type(space).__name__}"
        )
        raise TypeError(msg)
    return Space(space)


def _refuse_handles(atoms: Iterable[Atom | Undefined], role: str) -> None:
    """Refuse a live handle crossing a process boundary, in either direction.

    A handle is a name plus the engine that gives it meaning, and only the
    name can be pickled: `Space.__reduce__` answers `Space(name)`, so a
    worker handed one would open ITS OWN space of that name, empty, with
    nothing raised anywhere. Refusing is the only reading that cannot be
    silently wrong.
    """
    stack: list[Any] = list(atoms)
    while stack:
        node = stack.pop()
        if isinstance(node, Undefined):
            # An undefined answer still carries a term, and the term is what
            # would cross; its delay condition is text.
            stack.append(node.value)
            continue
        if isinstance(node, Handle):
            msg = (
                f"{role} is {node!s}, a handle on live engine state, and a "
                f"worker's engine is not this one: the same name in another "
                f"process names another space, with none of these atoms. "
                f"Answer the atoms themselves, save the space with "
                f"space.save(), or serve it with metta.remote."
            )
            raise MettaError(msg)
        if isinstance(node, Expression):
            stack.extend(node.children)


def _worker_ready() -> None:
    """Refuse with the boot's own reason rather than with a broken pool."""
    failure = _WORKER_BOOT_FAILURE
    if failure is None:
        return
    msg = f"this worker's engine did not boot, so it cannot run MeTTa: {failure}"
    raise MettaError(msg) from failure


def program(source: str, *, space: Symbol | str | None = None) -> list[list[Atom]]:
    """Run MeTTa source on THIS process's engine: one answer list per `!`.

    The work unit a ProcessPool takes, and an ordinary function everywhere
    else: in the parent `program(text)` is exactly `metta.run(text)`, which
    is what makes a plain `map(program, texts)` the pool's own differential
    oracle. Program TEXT crosses a process boundary and an engine does not,
    so this is what a worker is sent instead of a callable closing over a
    space.

        with metta.parallel.process_pool(3, boot="(= (sq $x) (* $x $x))") as p:
            for answers in p.map(metta.parallel.program, ["!(sq 3)", "!(sq 4)"]):
                print(answers)

    `space` names a space IN THE WORKER, by symbol or by exact string, the
    way `metta.space()` reads a name; a Space handle is refused. Answers
    cross as atoms by value, which is what `Atom.__reduce__` already is, and
    an answer that is a handle refuses rather than naming a space the worker
    owns.
    """
    _worker_ready()
    groups = _work_space(space).run(source)
    for group in groups:
        _refuse_handles(group, "an answer")
    return groups


def call(
    head: Symbol | str, *arguments: Any, space: Symbol | str | None = None
) -> list[Atom | Undefined]:
    """Apply a head the worker already knows to atoms, on THIS process's engine.

    The other work unit. Where `program` sends text to read and compile,
    this sends a NAME and its arguments, so a head the pool's `boot=`
    defined is called without re-reading its definition once per task:

        with metta.parallel.process_pool(3, boot="(= (sq $x) (* $x $x))") as p:
            list(p.starmap(metta.parallel.call, [(S.sq, 3), (S.sq, 4)]))

    Arguments and answers cross as atoms by value; a handle refuses in
    either direction, and so does an opaque grounded object, which is
    `Grounded.__reduce__`'s own refusal at the pickle boundary.
    """
    _worker_ready()
    if isinstance(head, Symbol):
        name = head
    elif isinstance(head, str):
        name = Symbol(head)
    else:
        msg = f"a work unit names its head by symbol or by string, not {type(head).__name__}"
        raise TypeError(msg)
    operands = [_to_atom(argument) for argument in arguments]
    _refuse_handles(operands, "an argument")
    answers: list[Atom | Undefined] = list(
        _work_space(space).eval(Expression([name, *operands]))
    )
    _refuse_handles(answers, "an answer")
    return answers


def _boot_engine(boot: str | None) -> None:
    """Start this worker's own engine and run the pool's boot program on it."""
    if forked():
        msg = (
            "this worker inherited a Prolog engine from the fork server "
            "it was forked from, which means an engine was booted while "
            "your program was being IMPORTED: forkserver runs __main__ "
            "once in the server and forks workers from it. Move the boot "
            "under `if __name__ == \'__main__\':`, which is where a spawn "
            "or forkserver start method needs it anyway, or keep it where "
            "it is and pass "
            "mp_context=multiprocessing.get_context(\'spawn\'), which "
            "gives each worker its own import and so its own engine."
        )
        raise MettaError(msg)
    runtime()
    home = _ambient_space()
    if boot:
        home.run(boot)


def _boot_worker(boot: str | None, reports: Any) -> None:
    """Boot one worker's own engine, once, before it takes any work.

    ProcessPoolExecutor's `initializer`, and it catches its own failure on
    purpose. An initializer that raises makes CPython log the traceback and
    kill the worker, and the caller then reads `BrokenProcessPool: A process
    in the process pool was terminated abruptly while the future was running
    or pending`, which names neither the engine nor the boot [measured
    2026-09-07 with a deliberately exploding initializer]. Recording the
    failure lets the worker survive to say what actually happened, on the
    first work unit that needs an engine.

    It reports its own boot seconds rather than leaving the cost a claim:
    the pool publishes them as `boot_seconds`.
    """
    global _WORKER_BOOT_FAILURE  # noqa: PLW0603  -- one per worker process, written once before that worker takes work
    started = time.perf_counter()
    try:
        _boot_engine(boot)
    except BaseException as exc:  # noqa: BLE001  -- a worker that cannot boot must survive to say so; _worker_ready re-raises this to the caller
        _WORKER_BOOT_FAILURE = exc
    reports.put((os.getpid(), time.perf_counter() - started))


def _callable_edges(item: Any) -> list[Any]:
    """What a callable carries with it, one hop out.

    The closure and global halves are `inspect.getclosurevars`, the standard
    library's own answer to this question: `nonlocals` are the free
    variables actually bound in `__closure__`, and `globals` are the entries
    of `__globals__` restricted to `co_names`, the names the function body
    LOOKS UP. That restriction is what keeps this from reading a whole
    module: a file that happens to hold a Space beside twenty functions does
    not make those twenty suspect. Ray's serializability inspector walks a
    callable through the same call [source:
    https://github.com/ray-project/ray/blob/master/python/ray/util/check_serialize.py,
    _inspect_func_serialization; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb].

    A module-level handle is the case only the global half sees: a function
    written `def work(n): return space.run(...)` beside `space = ...` has an
    EMPTY `__closure__` and names `space` as a global [measured 2026-09-07:
    `co_names` ('sp', 'run'), `__closure__` None].
    """
    if isinstance(item, functools.partial):
        return [item.func, *item.args, *item.keywords.values()]
    if isinstance(item, MethodType):
        return [item.__self__, item.__func__]
    if not isinstance(item, FunctionType):
        return []
    closed = inspect.getclosurevars(item)
    return [
        *closed.nonlocals.values(),
        *closed.globals.values(),
        *(item.__defaults__ or ()),
        *(item.__kwdefaults__ or {}).values(),
    ]


def _reachable(roots: list[Any]) -> Iterator[Any]:
    """Every object a submitted call plainly carries, callables two hops deep."""
    seen: set[int] = set()
    stack: list[tuple[Any, int]] = [(root, 0) for root in roots]
    while stack:
        item, hops = stack.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        yield item
        if isinstance(item, tuple | list | set | frozenset | deque):
            stack.extend((child, hops) for child in item)
        elif isinstance(item, dict):
            stack.extend((child, hops) for child in (*item.keys(), *item.values()))
        elif hops < _CALLABLE_HOPS:
            stack.extend((child, hops + 1) for child in _callable_edges(item))


def _refuse_engine_capture(fn: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    """Refuse work that reaches an engine THIS process owns.

    The hazard is not that a handle fails to cross; it is that it crosses.
    `Space.__reduce__` answers `Space(name)`, and a bound method of one
    pickles as well, so a worker receiving either opens its OWN space of
    that name, answers about it, and nothing raises [measured 2026-09-07:
    `pickle.loads(pickle.dumps(m.self))` answers `Space('&pyspace_1')` and
    `pickle.dumps(space.run)` succeeds].

    LIMIT, stated because it is real: the walk reads plain containers and
    two callable hops (closure cells, the globals a function NAMES, its
    defaults, a partial's parts, a bound method's receiver). A handle held
    inside a custom object, or three callables deep, is not seen. The work
    units above are the answer to that: `program` and `call` never take a
    handle in the first place.
    """
    for item in _reachable([fn, *args, *kwargs.values()]):
        if isinstance(item, _ENGINE_HANDLES):
            msg = (
                f"a worker process has its own engine, so this call cannot "
                f"cross to one: it reaches {item!r}, a handle on live state "
                f"in THIS process. A Space pickles by NAME, so the worker "
                f"would silently open its own space of that name. Send the "
                f"work instead of the handle: metta.parallel.program(text) "
                f"runs program text on the worker's engine, and "
                f"metta.parallel.call(head, *arguments) applies a head the "
                f"pool's boot= defined."
            )
            raise MettaError(msg)


class ProcessPool(_FanOut, ProcessPoolExecutor):
    """Worker PROCESSES that each boot an engine of their own.

    EnginePool's sibling one boundary out. A thread pool shares this
    process's spaces, equations and compiled functions, which is what makes
    a callable closing over a handle the right thing to write there; a
    process pool shares NOTHING, which is the point of it. Each worker boots
    its own engine once, from the same fast image a fresh `metta` process
    boots from, and then runs work units that carry only text and atoms:

        with metta.parallel.process_pool(3, boot="(= (sq $x) (* $x $x))") as p:
            for answers in p.map(metta.parallel.program, programs):
                print(answers)

    Use it when isolation is the point: one program must not see another's
    equations, a run must not be able to corrupt the caller's space, or a
    workload must survive a worker that dies. Use `pool()` instead when the
    work shares knowledge, which is most work; a thread there costs an
    engine attachment and a worker here costs a whole boot.

    `boot` is MeTTa program text every worker runs once after its engine
    starts, so a head `call` names is compiled per worker rather than per
    task.

    ONE TRAP, and it is the forkserver's rather than this pool's. On Linux
    the default start method runs your `__main__` ONCE in a fork server and
    forks each worker from it, so an engine your module boots at IMPORT time
    is booted in that server and inherited by every worker across a fork,
    which is the one thing SWI-Prolog does not survive. Every work unit in
    such a worker refuses, naming this. Keep the boot under
    `if __name__ == "__main__":`, which spawn and forkserver both want
    anyway, or pass `mp_context=multiprocessing.get_context("spawn")` and
    let each worker do its own import [measured 2026-09-07: a probe with a
    module-level `MeTTa()` had all three forkserver workers refuse, and the
    same probe with the boot under the main guard answered].

    Assumes:
      - the start method does not fork this process. `fork` is refused at
        construction: SWI-Prolog does not survive one, and `_engine`'s
        after-fork handler would leave the child refusing every crossing.
    Guarantees:
      - each worker holds its own engine and its own spaces [tested:
        test_the_process_pool_runs_three_programs_in_three_workers;
        commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
      - a callable reaching a Space, MeTTa, Runtime or EnginePool refuses at
        submit rather than opening a different space in the worker [tested:
        test_a_closure_over_a_space_refuses_at_submit; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
      - a worker whose engine did not boot says why on its first work unit,
        rather than breaking the pool with BrokenProcessPool [tested:
        test_a_worker_that_cannot_boot_says_why; commit=0179a14353a925115d545fc3ea0dc67eab4e4ecb]
    Owns:
      - one process, one Prolog engine and one boot per worker, from the
        first submit until shutdown(); and one SimpleQueue carrying the
        workers' boot timings, closed by shutdown().
    Decides:
      - workers defaults to os.cpu_count(), as EnginePool's does.
    """

    def __init__(
        self,
        workers: int | None = None,
        *,
        boot: str | None = None,
        mp_context: Any = None,
    ) -> None:
        """Start no worker yet: ProcessPoolExecutor spawns one when work arrives."""
        if workers is None:
            workers = os.cpu_count() or 1
        if not isinstance(workers, int) or isinstance(workers, bool):
            msg = f"workers must be an int, not {type(workers).__name__}"
            raise TypeError(msg)
        if workers < 1:
            msg = f"a pool needs at least one worker, not {workers}"
            raise ValueError(msg)
        if boot is not None and not isinstance(boot, str):
            msg = (
                f"boot is MeTTa program text every worker runs after its "
                f"engine starts, not {type(boot).__name__}"
            )
            raise TypeError(msg)
        context = (
            multiprocessing.get_context(_start_method()) if mp_context is None else mp_context
        )
        if context.get_start_method() == "fork":
            msg = (
                "a process pool cannot use the fork start method: a forked "
                "child inherits this process's Prolog engine, and SWI-Prolog "
                "does not survive a fork, so every crossing in that child "
                "refuses. Use forkserver, which is this pool's default on "
                "Linux, or spawn: "
                "ProcessPool(mp_context=multiprocessing.get_context('forkserver'))."
            )
            raise MettaError(msg)
        self._workers = workers
        self._reports = context.SimpleQueue()
        self._reports_open = True
        self._boots: dict[int, float] = {}
        self._closed = False
        super().__init__(
            max_workers=workers,
            mp_context=context,
            initializer=_boot_worker,
            initargs=(boot, self._reports),
        )

    @override
    def submit[R](self, fn: Callable[..., R], /, *args: Any, **kwargs: Any) -> Future[R]:
        """Queue one call on a worker process and answer its Future.

        Executor.submit, with one refusal in front of it: a call that
        reaches an engine handle in this process is refused HERE, where the
        remedy can be named, rather than crossing and answering about the
        worker's own space.
        """
        _refuse_engine_capture(fn, args, kwargs)
        return super().submit(fn, *args, **kwargs)

    @override
    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Executor's teardown, and the close of the boot-timing queue.

        The timings already read stay readable afterwards, because the queue
        is drained before it is closed.
        """
        super().shutdown(wait=wait, cancel_futures=cancel_futures)
        self._closed = True
        if self._reports_open:
            self._drain_boots()
            self._reports_open = False
            self._reports.close()

    def _drain_boots(self) -> None:
        """Take whatever boot timings have arrived, without waiting for more."""
        while self._reports_open and not self._reports.empty():
            pid, seconds = self._reports.get()
            self._boots[int(pid)] = float(seconds)

    @property
    def boot_seconds(self) -> dict[int, float]:
        """Seconds each started worker spent booting its engine, by pid.

        Empty until the first submit, because ProcessPoolExecutor starts a
        worker when there is work for it rather than at construction. A
        worker whose boot FAILED still reports its seconds; what it failed
        at arrives on the first work unit instead.
        """
        self._drain_boots()
        return dict(self._boots)

    @property
    def workers(self) -> int:
        """How many worker processes, and therefore engines, this pool holds."""
        return self._workers

    @property
    def closed(self) -> bool:
        """Whether shutdown() has run."""
        return self._closed

    def __len__(self) -> int:
        """How many worker processes this pool holds, as EnginePool answers."""
        return self._workers

    def __repr__(self) -> str:
        """The pool's shape and whether it is still taking work."""
        state = "closed" if self._closed else "live"
        return f"<ProcessPool workers={self._workers} {state}>"


def process_pool(
    workers: int | None = None, *, boot: str | None = None, mp_context: Any = None
) -> ProcessPool:
    """A pool of worker processes that each boot their own engine.

    `pool()`'s sibling one boundary out; see ProcessPool for what each
    boundary shares and what it does not.

        with metta.parallel.process_pool(4, boot=rules) as p:
            answers = list(p.map(metta.parallel.program, programs))

    workers defaults to os.cpu_count().
    """
    return ProcessPool(workers, boot=boot, mp_context=mp_context)


def _ambient_space() -> Space:
    from . import current_space, engine  # noqa: PLC0415 -- root owns the lazy default context

    return engine().space(current_space())


def _ensure_thread_library(owner: Space) -> None:
    owner.answers(
        Expression(
            [
                Symbol("import!"),
                owner,
                Expression([Symbol("library"), Symbol("lib_thread")]),
            ]
        )
    ).one()


def _call(owner: Space, head: str, *arguments: Any):
    _ensure_thread_library(owner)
    return owner.answers(Expression([Symbol(head), *(_to_atom(arg) for arg in arguments)]))


class FutureSpace(Space):
    """A spawned computation's ordinary answer space with lifecycle verbs.

    Abandoning one follows Python's own future semantics: the computation
    keeps running, exactly as a concurrent.futures future would, and the
    garbage collector emits asyncio's kind of ResourceWarning when a
    handle dies without anyone having observed settlement, so an
    accidentally dropped infinite producer names itself instead of
    spinning silently. ``cancel()`` remains the deliberate stop.
    """

    def __init__(self, space: Space, owner: Space) -> None:  # noqa: D107 -- the enclosing type defines the future-space construction boundary
        super().__init__(space.name, _runtime=space.runtime)
        self._owner = owner
        # The finalizer must not touch self or the engine at interpreter
        # shutdown, so settlement observation rides a shared cell.
        self._settlement = {"observed": False}
        _weakref.finalize(self, _warn_abandoned, space.name, self._settlement)

    def wait(self):
        """Wait until evaluation settles, then lazily expose every stored answer."""
        answers = _call(self._owner, "await", self)
        self._settlement["observed"] = True
        return answers

    def settled(self) -> bool:
        """Whether the computation has finished, without waiting."""
        finished = bool(_call(self._owner, "settled?", self).one())
        if finished:
            self._settlement["observed"] = True
        return finished

    def cancel(self) -> bool:
        """Stop a pending computation, answering whether it was stopped."""
        stopped = bool(_call(self._owner, "cancel", self).one())
        self._settlement["observed"] = True
        return stopped

    def __iter__(self) -> Iterator[Atom]:
        """Yield each answer occurrence after it lands, until settlement."""
        subscription = self.subscribe(
            Variable("_future_answer"), on=SubscriptionEdge.add
        )
        try:
            current, watermark = self._iteration_snapshot()
            yielded = list(current)
            yield from current
            pending = subscription.drain()
            while True:
                for event in pending:
                    sequence = getattr(event, "_sequence", None)
                    if sequence is not None and sequence <= watermark:
                        continue
                    yielded.append(event.atom)
                    yield event.atom
                if self.settled():
                    # Settlement follows every engine-produced answer. One
                    # final reconciliation also retains any ordinary space
                    # write that did not carry a future publication position.
                    final = list(_unseen_occurrences(self.atoms(), yielded))
                    yield from final
                    return
                pending = subscription.wait(0.05)
        finally:
            subscription.cancel()

    def _iteration_snapshot(self) -> tuple[list[Atom], int]:
        """The initial answer bag and its exact publication watermark."""
        watermark, wires = self._rt.apply_must("metta_py_future_snapshot", self._space)
        return [_atom_from_wire(wire) for wire in wires], int(watermark)


def _warn_abandoned(name: str, settlement: dict) -> None:
    if not settlement["observed"]:
        import warnings  # noqa: PLC0415  -- the finalizer must import nothing at module load

        warnings.warn(
            f"FutureSpace {name} was abandoned while possibly pending; "
            f"wait() or cancel() it",
            ResourceWarning,
            stacklevel=2,
        )


def _unseen_occurrences(current: list[Atom], seen: list[Atom]) -> Iterator[Atom]:
    """Yield an ordered multiset difference in expected linear time."""
    unmatched = Counter(seen)
    for atom in current:
        if unmatched[atom]:
            unmatched[atom] -= 1
            continue
        yield atom


def _future(owner: Space, head: str, *arguments: Any) -> FutureSpace:
    result = _call(owner, head, *arguments).one()
    if not isinstance(result, Space):
        msg = f"{head} returned {result!r}, not its promised future space"
        raise MettaError(msg)
    return FutureSpace(result, owner)


def spawn(expression: Any) -> FutureSpace:
    """Start one expression now and return the space its answers fill."""
    owner = _ambient_space()
    return _future(owner, "spawn", expression)


def every(seconds: float, expression: Any) -> FutureSpace:
    """Repeat one expression at each interval until its future is cancelled."""
    owner = _ambient_space()
    return _future(owner, "every", seconds, expression)


def race(*expressions: Any) -> Any:
    """Return the first successful answer and cancel the remaining branches."""
    if not expressions:
        msg = "race needs at least one expression"
        raise ValueError(msg)
    return _call(_ambient_space(), "par-race", Expression(expressions)).one()


def par_map(function: Any, items: Iterable[Any]) -> Expression:
    """Evaluate a unary MeTTa function concurrently, preserving input order."""
    result = _call(_ambient_space(), "par-map", function, Expression(items)).one()
    if not isinstance(result, Expression):
        msg = f"par-map returned {result!r}, not its promised result expression"
        raise MettaError(msg)
    return result


class Channel:
    """A bounded or unbounded lib_thread mailbox in Python dress."""

    def __init__(self, owner: Space, handle: Any) -> None:  # noqa: D107 -- channel() is the public constructor and documents this state
        self._owner = owner
        self._handle = handle
        self._closed = False
        # weakref.finalize keeps the callback alive without keeping this
        # Channel alive. A static callback is load-bearing: a bound method
        # would retain self and therefore prevent the collection it awaits.
        # https://docs.python.org/3.14/library/weakref.html#weakref.finalize
        self._finalizer = _weakref.finalize(
            self, Channel._reap, self._owner.runtime, self._handle
        )

    @staticmethod
    def _reap(rt: Runtime, handle: Any) -> None:
        try:
            # A finalizer can run on an arbitrary bare Python thread. Use the
            # eager bridge crossing used by Cursor._reap: opening a lazy
            # Answers cursor here leaves a Janus query object's destructor on
            # that foreign thread, which can unregister atoms after its
            # temporary SWI engine has detached.
            rt.apply_must("channel_close", handle)
        except MettaError:
            logger.debug("channel finalization found an unavailable engine", exc_info=True)

    def send(self, term: Any) -> bool:
        """Block until capacity admits one copied term."""
        return bool(_call(self._owner, "send", self._handle, term).one())

    def recv(self, *, deadline: float | None = None) -> Any:
        """Take one term, raising Timeout when a finite wait is quiet."""
        arguments = (self._handle,) if deadline is None else (self._handle, deadline)
        answers = _call(self._owner, "recv", *arguments)
        sentinel = object()
        result = answers.first(default=sentinel)
        if result is sentinel:
            if deadline is None:
                msg = "channel receive ended without an answer"
                raise MettaError(msg)
            msg = f"no channel message arrived within {deadline} seconds"
            raise Timeout(msg)
        return result

    def try_recv(self) -> Any | None:
        """Take one waiting term or return None without blocking."""
        return _call(self._owner, "try-recv", self._handle).first(default=None)

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return int(_call(self._owner, "channel-size", self._handle).one())

    def close(self) -> None:
        """Destroy this mailbox. Closing twice is a no-op."""
        if self._closed:
            return
        _call(self._owner, "channel-close", self._handle).one()
        self._closed = True
        self._finalizer.detach()

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.close()


def channel(*, max: int | None = None) -> Channel:  # noqa: A002 -- max is the ruled public keyword
    """Create a mailbox; max bounds queued terms and blocks full senders."""
    owner = _ambient_space()
    arguments = () if max is None else (max,)
    return Channel(owner, _call(owner, "channel", *arguments).one())
