"""Purpose: keep lazy evaluation selections on their asynchronous engine worker.

Assumes: an evaluation returns Answers or a closable stream for each target.
Guarantees: iteration, refusal and cleanup run on the owning worker; Answers
  replay their cached prefix while streams consume once [tested:
  test_async_evaluation_choices_preserve_demand_and_replay; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Owns resources: one tracked group owns every source in an acquired batch.
  Closing a view releases its source; closing the parent releases the group.
  Failed cleanup remains tracked for retry [tested:
  test_async_evaluation_cleanup_is_owned_and_retryable; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Guarded by: the worker serializes source access. _opening orders acquisition
  and asynchronous release; _state_changed protects synchronous shutdown.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any, Self

from .aio import _acquire, _raise_lifecycle_failures, _shielded
from .errors import MettaError
from .results import Answers

if TYPE_CHECKING:
    from ._space import Space
    from .aio import AsyncMeTTa


_END = object()


class _EvaluationGroup:
    """One acquisition, including a batch's cancellation and close obligations."""

    def __init__(self, owner: AsyncMeTTa) -> None:
        self.owner = owner
        self.sources: tuple[Any, ...] = ()
        self._live: set[int] = set()
        self._opening = asyncio.Lock()
        self._state_changed = threading.Condition()
        self._acquiring = False

    async def open(self, execute: Callable[[Space], Any], *, batch: bool) -> Any:
        """Publish ownership before the worker can acquire any source."""
        async with self._opening:
            with self._state_changed:
                self._acquiring = True
            try:
                self.owner._track_subscription(self)

                def capture(space: Space) -> None:
                    result = execute(space)
                    with self._state_changed:
                        self.sources = tuple(result) if batch else (result,)
                        self._live = set(range(len(self.sources)))

                await _acquire(
                    self.owner.call(capture),
                    lambda _value: self.owner._subscription_call(lambda _space: self._close_all()),
                )
            except BaseException:
                with self._state_changed:
                    live = bool(self._live)
                if not live:
                    self.owner._forget_subscription(self)
                raise
            finally:
                with self._state_changed:
                    self._acquiring = False
                    self._state_changed.notify_all()
        views = [EvaluationView(self, index) for index in range(len(self.sources))]
        return views if batch else views[0]

    def _close(self, index: int) -> None:
        """Release one source on the worker, retaining a failed close."""
        with self._state_changed:
            if index not in self._live:
                return
        self.sources[index].close()
        with self._state_changed:
            self._live.discard(index)
            empty = not self._live
        if empty:
            self.owner._forget_subscription(self)

    def _close_all(self) -> None:
        failures = []
        for index in range(len(self.sources)):
            try:
                self._close(index)
            except BaseException as error:  # noqa: BLE001 -- release every owned source even after interruption
                failures.append(error)
        _raise_lifecycle_failures("closing asynchronous evaluation sources failed", failures)

    async def _release(self) -> None:
        """Parent close waits for acquisition, then attempts every source."""
        async with self._opening:
            await self.owner._subscription_call(lambda _space: self._close_all())
            self.owner._forget_subscription(self)

    def _stop(self) -> None:
        """The parent's synchronous stop must run outside an event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            msg = "a live evaluation needs await aclose(); stop() runs outside an event loop"
            raise MettaError(msg)
        with self._state_changed:
            self._state_changed.wait_for(lambda: not self._acquiring)
        asyncio.run(self._release())

    def _cached(self, index: int, position: int, *, rows: bool) -> Any:
        source = self.sources[index]
        if isinstance(source, Answers):
            if position < len(source._cache):
                if rows:
                    row = source._row_cache[position]
                    if row is None:
                        msg = f"answer {source._cache[position]!r} carries no variable row"
                        raise TypeError(msg)
                    return row
                return source._cache[position]
            if source._error is not None:
                raise source._error
        return _END

    def _pull(self, index: int, position: int, *, rows: bool) -> Any:
        source = self.sources[index]
        if isinstance(source, Answers):
            source._pull(position)
            value = self._cached(index, position, rows=rows)
        else:
            value = next(source, _END)
        if value is _END:
            self._close(index)
        return value

    async def pull(self, index: int, position: int, *, rows: bool) -> Any:
        """Read a frozen prefix locally and advance only through the worker."""
        with self._state_changed:
            closed = index not in self._live
        if closed:
            return self._cached(index, position, rows=rows)
        try:
            return await self.owner.call(lambda _space: self._pull(index, position, rows=rows))
        except BaseException as error:
            try:
                await self.close(index)
            except BaseException as cleanup:  # noqa: BLE001 -- preserve cancellation and its cleanup failure
                msg = "asynchronous evaluation and cleanup failed"
                raise BaseExceptionGroup(msg, [error, cleanup]) from None
            raise

    async def close(self, index: int) -> None:
        with self._state_changed:
            closed = index not in self._live
        if not closed:
            await _shielded(self.owner._subscription_call(lambda _space: self._close(index)))


class EvaluationView:
    """A lazy answer selection with asynchronous iteration and release.

    The answers selection replays on each async-for. The stream selection
    consumes its single source. Both retain the engine's answer values.
    """

    def __init__(self, group: _EvaluationGroup, index: int, *, rows: bool = False) -> None:
        self._group = group
        self._index = index
        self._rows = rows
        self._position = 0
        self._pulling = asyncio.Lock()

    @property
    def columns(self) -> tuple[str, ...]:
        """The caller-variable names captured by an answers selection."""
        return tuple(getattr(self._group.sources[self._index], "columns", ()))

    @property
    def rows(self) -> EvaluationView:
        """The caller bindings paired with each replayable answer."""
        if not isinstance(self._group.sources[self._index], Answers):
            msg = "a stream has no replayable caller rows; select answer='answers' or 'rows'"
            raise TypeError(msg)
        return EvaluationView(self._group, self._index, rows=True)

    def __aiter__(self) -> AsyncIterator[Any]:
        if isinstance(self._group.sources[self._index], Answers):
            return self._replay()
        return self

    async def _replay(self) -> AsyncIterator[Any]:
        position = 0
        while True:
            value = await self._group.pull(self._index, position, rows=self._rows)
            if value is _END:
                return
            yield value
            position += 1

    async def __anext__(self) -> Any:
        async with self._pulling:
            value = await self._group.pull(self._index, self._position, rows=self._rows)
            if value is _END:
                raise StopAsyncIteration
            self._position += 1
            return value

    async def aclose(self) -> None:
        """Release this selection; a failed release remains retryable."""
        await self._group.close(self._index)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.aclose()
