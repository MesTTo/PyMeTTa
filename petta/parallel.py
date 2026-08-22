"""Purpose: evaluate on more than one core. An EnginePool owns a fixed set of
worker threads, each holding its own attached Prolog engine for the pool's
lifetime, and runs ordinary Python callables on them. Because a worker's
engine is private to its thread, the process lock that serialises the home
engine does not apply to it, so the branches genuinely run at once.

This is the Python-side fan-out. MeTTa.parallel() is the in-engine fan-out
through hyperpose, below a single janus call. They compose: a pool worker may
itself evaluate a hyperpose.

    with petta.parallel.pool(workers=8) as p:
        answers = p.map(lambda n: m.one(f"(solve {n})"), range(64))

Assumes:
  - petta._engine.engine_thread attaches an engine to a bare foreign thread
    and detaches exactly the engine it attached [tested
    test_engine_thread_owns_only_its_attachment]
  - PeTTa's shared Prolog structures carry their own mutexes, so concurrent
    engines do not corrupt them: '$petta_specializer' in specializer.pl,
    '$petta_native_storage' in spaces.pl, metta_loader around
    process_metta_string in filereader.pl, and a per-function mutex in
    lib_memo.pl [source 2026-08-15]
Guarantees:
  - a worker engine answers exactly what the home engine answers
    [tested test_pool_agrees_with_the_home_engine]
  - map answers in input order however the workers finish
    [tested test_map_answers_in_input_order]
  - a worker exception is raised to the caller rather than swallowed: one
    plainly, several together as one ExceptionGroup in input order
    [tested test_map_raises_every_failure_in_input_order]
  - branches really run at once [measured 2026-08-15: 1.94x, 3.90x and 7.26x
    at 2, 4 and 8 workers on a 12ms MeTTa evaluation, ai-tmp/pool/lock_check.py;
    tested test_pool_runs_work_concurrently]
  - every worker releases its engine on close, including after an exception
    [tested test_close_releases_every_engine]
  - a closed pool refuses new work naming the cause rather than hanging
    [tested test_closed_pool_refuses_work]
Fails when:
  - the work is not engine-bound. A pool costs one thread and one engine per
    worker, so fanning out calls that are already fast buys queueing overhead
    and nothing else.
  - the callables mutate shared Python state. The pool serialises nothing on
    the Python side; that is the caller's problem, as with any thread pool.
Owns:
  - one daemon thread and one attached Prolog engine per worker, from start
    until close(). close() is idempotent and runs from __exit__.
Guarded by:
  - _state_lock publishes the pool's state and worker list; the work queue is
    a queue.Queue and needs no further locking.
Decides:
  - workers defaults to os.cpu_count(), the same default library(thread)'s
    jobs/2 uses for concurrent_and/3.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import logging
import os
import queue
import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, as_completed
from typing import Any, Self

from ._engine import engine_thread, runtime
from .errors import PettaError

logger = logging.getLogger(__name__)


__all__ = ["EnginePool", "pool"]

# What a worker takes off the queue: the future to settle, and the call.
_Job = tuple["Future[Any]", Callable[..., Any], tuple[Any, ...], dict[str, Any]]


class EnginePool:
    """Worker threads that each hold their own Prolog engine.

    Construct through pool() or MeTTa.pool(). The pool starts its workers
    eagerly, so that a first map() does not pay engine attachment, and holds
    them until close(): attaching and detaching an engine is documented as
    relatively expensive (SWI manual section 10.6.1).
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
                name=f"petta-pool-{index}",
                daemon=True,
            )
            thread.start()
            self._started.append(thread)
        try:
            self._ready.wait()
        except threading.BrokenBarrierError as exc:
            self.close()
            msg = "a pool worker could not attach its Prolog engine"
            raise PettaError(
                msg
            ) from self._start_error or exc
        if self._start_error is not None:
            failure = self._start_error
            self.close()
            msg = "a pool worker could not attach its Prolog engine"
            raise PettaError(msg) from failure

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
            logger.exception("a petta pool worker stopped")

    def _serve(self) -> None:
        while True:
            job = self._work.get()
            if job is None:
                return
            future, fn, args, kwargs = job
            if not future.set_running_or_notify_cancel():
                continue
            try:
                result = fn(*args, **kwargs)
            except BaseException as exc:  # noqa: BLE001
                # A BaseException crosses to the caller too: a worker that
                # swallowed KeyboardInterrupt would hide it entirely.
                future.set_exception(exc)
            else:
                future.set_result(result)

    # -------------------------------------------------------------------- submit

    def submit[R](self, fn: Callable[..., R], /, *args: Any, **kwargs: Any) -> Future[R]:
        """Queue one call on a worker and answer its Future."""
        with self._state_lock:
            if self._closed:
                msg = (
                    "this pool is closed and cannot take new work; "
                    "build another with petta.parallel.pool()"
                )
                raise PettaError(
                    msg
                )
        future: Future[R] = Future()
        self._work.put((future, fn, args, kwargs))
        return future

    def map[T, R](self, fn: Callable[[T], R], items: Iterable[T]) -> list[R]:
        """Run fn on every item across the workers, in input order.

        Answers a list, not an iterator, because the whole point is that the
        work already ran. One failure raises plainly; several raise together
        as one ExceptionGroup in INPUT order, so what a caller sees never
        depends on which worker lost the race and no failure after the first
        goes unreported; the remaining work is left to finish rather than
        half-cancelled.
        """
        return self._gather([self.submit(fn, item) for item in items])

    def starmap[R](self, fn: Callable[..., R], items: Iterable[Iterable[Any]]) -> list[R]:
        """map() for a callable of several arguments, spelled as itertools does."""
        return self._gather([self.submit(fn, *tuple(item)) for item in items])

    def _gather[R](self, futures: list[Future[R]]) -> list[R]:
        """Every future's result, or every failure, in INPUT order.

        The loop finishes even after a failure, and that is the point rather
        than tidiness: a Future whose result is never fetched drops its
        exception without a word, so leaving the rest undrained would lose
        every failure after the first. One failure raises plainly; several
        raise as one group, the library's raise_for_errors policy, and
        BaseExceptionGroup picks the Exception-only subclass itself when it
        can.

        BaseException is caught deliberately. A worker's KeyboardInterrupt has
        to reach the caller, grouped if it arrived beside other failures, and
        filtering it out for not being an Exception is exactly how an
        interrupt gets swallowed.
        """
        results: list[R] = []
        failures: list[BaseException] = []
        for future in futures:
            try:
                results.append(future.result())
            except BaseException as exc:  # noqa: BLE001
                failures.append(exc)
        if len(failures) == 1:
            raise failures[0]
        if failures:
            msg = f"{len(failures)} of {len(futures)} pool tasks failed"
            raise BaseExceptionGroup(
                msg, failures
            )
        return results

    # --------------------------------------------------------------- lifecycle

    def close(self, wait: bool = True) -> None:  # noqa: FBT001, FBT002  -- the boolean is established API data and positional compatibility is part of the call shape
        """Stop every worker and release every engine. Idempotent."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        for _ in self._started:
            self._work.put(None)
        if not wait:
            return
        for thread in self._started:
            thread.join(timeout=30)
        still_running = [t.name for t in self._started if t.is_alive()]
        if still_running:
            msg = f"pool workers did not stop within 30s: {', '.join(still_running)}"
            raise PettaError(
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
        self.close()

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self._workers

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        state = "closed" if self._closed else "live"
        return f"<EnginePool workers={self._workers} {state}>"


def pool(workers: int | None = None) -> EnginePool:
    """A pool of worker threads that each hold their own Prolog engine.

    Use it as a context manager so the engines are released:

        with petta.parallel.pool(workers=4) as p:
            answers = p.map(lambda n: m.one(f"(fib {n})"), range(20))

    workers defaults to os.cpu_count().
    """
    return EnginePool(workers)


def imap_unordered[T, R](
    engine_pool: EnginePool, fn: Callable[[T], R], items: Iterable[T]
) -> Iterator[R]:
    """Yield results as they finish rather than in input order.

    Use this when the caller can start consuming before the slowest item
    lands; map() is the right default because input order is what almost
    every caller means.
    """
    futures = [engine_pool.submit(fn, item) for item in items]
    for future in as_completed(futures):
        yield future.result()
