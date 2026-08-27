"""Purpose: evaluate on more than one core. An EnginePool owns a fixed set of
worker threads, each holding its own attached Prolog engine for the pool's
lifetime, and runs ordinary Python callables on them. Because a worker's
engine is private to its thread, the process lock that serialises the home
engine does not apply to it, so the branches genuinely run at once.

This is the Python-side fan-out. Space.parallel() is the in-engine fan-out
through hyperpose, below a single janus call. They compose: a pool worker may
itself evaluate a hyperpose.

    with metta.parallel.pool(workers=8) as p:
        answers = p.map(lambda n: m.eval(S.solve(n))[0], range(64))

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
  - package coordination functions evaluate lib_thread in the ambient space;
    spawned and repeating computations stay Space handles whose answers may
    be iterated as they arrive [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
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
  - every Python and engine-backed spawn door snapshots ContextVars at launch,
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

import contextvars
import logging
import os
import queue
import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, as_completed
from typing import Any, Self

from ._engine import engine_thread, runtime
from ._space import Space
from .atoms import Atom, Expression, Symbol, Variable, _to_atom
from .errors import MettaError, Timeout

logger = logging.getLogger(__name__)


__all__ = [
    "Channel",
    "EnginePool",
    "FutureSpace",
    "channel",
    "every",
    "par_map",
    "pool",
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
        self.close()

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self._workers

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        state = "closed" if self._closed else "live"
        return f"<EnginePool workers={self._workers} {state}>"


def pool(workers: int | None = None) -> EnginePool:
    """A pool of worker threads that each hold their own Prolog engine.

    Use it as a context manager so the engines are released:

        with metta.parallel.pool(workers=4) as p:
            answers = p.map(lambda n: m.eval(S.fib(n))[0], range(20))

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
    """A spawned computation's ordinary answer space with lifecycle verbs."""

    def __init__(self, space: Space, owner: Space) -> None:  # noqa: D107 -- the enclosing type defines the future-space construction boundary
        super().__init__(space.name, _runtime=space.runtime)
        self._owner = owner

    def wait(self):
        """Wait until evaluation settles, then lazily expose every stored answer."""
        return _call(self._owner, "await", self)

    def settled(self) -> bool:
        """Whether the computation has finished, without waiting."""
        return bool(_call(self._owner, "settled?", self).one())

    def cancel(self) -> bool:
        """Stop a pending computation, answering whether it was stopped."""
        return bool(_call(self._owner, "cancel", self).one())

    def __iter__(self) -> Iterator[Atom]:
        """Yield each answer occurrence after it lands, until settlement."""
        subscription = self.subscribe(Variable("_future_answer"), on="add")
        seen: list[Atom] = []
        try:
            while True:
                current = self.atoms()
                yield from _unseen_occurrences(current, seen)
                seen = current
                if self.settled():
                    # Settlement is terminal for future-produced answers. One
                    # final snapshot closes the snapshot-to-settled race.
                    yield from _unseen_occurrences(self.atoms(), seen)
                    return
                subscription.wait(0.05)
        finally:
            subscription.cancel()


def _unseen_occurrences(current: list[Atom], seen: list[Atom]) -> Iterator[Atom]:
    """Yield the multiset difference from one ordered atom snapshot."""
    unmatched = list(seen)
    for atom in current:
        try:
            unmatched.remove(atom)
        except ValueError:
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

    def __len__(self) -> int:  # noqa: D105 -- the enclosing channel contract supplies the size meaning
        return int(_call(self._owner, "channel-size", self._handle).one())

    def close(self) -> None:
        """Destroy this mailbox. Closing twice is a no-op."""
        if self._closed:
            return
        _call(self._owner, "channel-close", self._handle).one()
        self._closed = True

    def __enter__(self) -> Self:  # noqa: D105 -- context entry returns the live mailbox
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105 -- context exit closes the mailbox
        self.close()


def channel(*, max: int | None = None) -> Channel:  # noqa: A002 -- max is the ruled public keyword
    """Create a mailbox; max bounds queued terms and blocks full senders."""
    owner = _ambient_space()
    arguments = () if max is None else (max,)
    return Channel(owner, _call(owner, "channel", *arguments).one())
