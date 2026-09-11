"""Purpose: keep asynchronous cursor, subscription and context views on their owner worker.

Owns resources: views retain their worker resources until close; cancelled
acquisition releases the completed resource before propagating cancellation
[tested: test_aio_cancelled_subscription_registration_cancels_it;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Guarded by: _opening serializes acquisition and _state_changed publishes
subscription ownership across worker and event-loop threads [source:
extensions/python/metta/aio/_views.py:371; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Callable
from types import TracebackType
from typing import Any, Final, Self

import metta._spaces.lifetime as _scope
from metta._atoms.designation import _UNSET
from metta._atoms.factories import Atom, Symbol, Undefined
from metta._atoms.names import OperatorRecipe, operator_attribute_target
from metta._errors.errors import MettaError, Timeout
from metta._faces.space import Space
from metta._spaces.results import Rows
from metta.aio import _worker
from metta.subscribe import _capacity
from metta.vocabularies import (
    SubscriptionEdge,
)

logger = logging.getLogger(__name__)

class AsyncSaga:
    """The awaitable context-manager twin of :class:`metta._history.saga.Saga`."""

    __slots__ = ("_acquiring", "_am", "_receipts", "_saga")

    def __init__(self, am: _worker.AsyncMeTTaBase, receipts: _worker.AsyncMeTTaBase) -> None:
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

            cleanup_error = await _worker._settled(
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

    def __init__(self, am: _worker.AsyncMeTTaBase, world: Any) -> None:
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

    def __init__(self, am: _worker.AsyncMeTTaBase) -> None:
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

    def __init__(self, am: _worker.AsyncMeTTaBase, facts: tuple) -> None:
        self._am = am
        self._facts = facts
        self._cm: Any = None

    async def __aenter__(self) -> _worker.AsyncMeTTaBase:
        facts = self._facts
        am = self._am

        def enter(space: Space) -> Any:
            # Both halves on ONE crossing: a cancellation between building the
            # block and entering it used to leave the facts installed with no
            # block to remove them.
            block = space.assuming(*facts)
            block.__enter__()
            return block

        self._cm = await _worker._acquire(
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

    def __init__(self, am: _worker.AsyncMeTTaBase, prepared: Any) -> None:
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
                self._cursor = await _worker._acquire(
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
        await _worker._shielded(self._release())

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
        am: _worker.AsyncMeTTaBase,
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
        self._loop: asyncio.AbstractEventLoop | None = None
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
                self._loop = loop
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

                am = self._am
                am._track_subscription(self)
                try:
                    await _worker._acquire(
                        am.call(lambda m: self._register(m, deliver)),
                        lambda acquired: am._subscription_call(
                            lambda _m: acquired.cancel()
                        ),
                    )
                except BaseException:
                    am._forget_subscription(self)
                    raise
                with self._state_changed:
                    if self._closed:
                        msg = "this subscription closed during registration"
                        raise MettaError(msg)
                    orphaned = self._orphaned
                if orphaned:
                    self._retire_closed_loop()
                # A queue reachable before its registration succeeded is one a
                # consumer waits on forever: nothing owns it, and nothing will
                # ever write to it
                # [tested test_aio_a_failed_subscription_publishes_no_queue].
                self._queue = events
            return self._queue

    def _register(self, space: Space, deliver: Callable[..., Any]) -> Any:
        """Publish ownership before the worker acknowledges acquisition."""
        with self._state_changed:
            if self._closed:
                msg = "this subscription closed before registration"
                raise MettaError(msg)
            self._acquiring = True
        subscription = None
        try:
            subscription = space.subscribe(
                self._pattern, deliver, on=self._on, where=self._where
            )
            with self._state_changed:
                self._subscription = subscription
            _scope.own("cleanup", self._stop)
        except BaseException:
            if subscription is not None:
                with _scope.suspend():
                    subscription.cancel()
                with self._state_changed:
                    self._subscription = None
            raise
        else:
            return subscription
        finally:
            with self._state_changed:
                self._acquiring = False
                self._state_changed.notify_all()

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
        await _worker._shielded(self._release())

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
        if self._loop is not None and self._queue is not None:
            with contextlib.suppress(RuntimeError):
                self._loop.call_soon_threadsafe(self._end, self._queue)

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

    def __init__(self, am: _worker.AsyncMeTTaBase) -> None:
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

    def __init__(self, am: _worker.AsyncMeTTaBase) -> None:
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

    def __init__(self, am: _worker.AsyncMeTTaBase, name: str) -> None:
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

    def __init__(self, am: _worker.AsyncMeTTaBase, recipe: OperatorRecipe) -> None:
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
