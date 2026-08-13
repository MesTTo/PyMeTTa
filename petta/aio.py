"""Purpose: the same engine without blocking an event loop. AsyncMeTTa
proxies a MeTTa space onto one dedicated worker thread that holds an
attached Prolog engine, the aiosqlite architecture (one thread per
connection, a request queue, results delivered back through the loop), so
awaiting a long query lets every other coroutine keep running. One engine
per process stays the rule: calls are serialized, and the win is a live
event loop, never parallel evaluation.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import asyncio
import queue
import threading
from typing import Any, Callable

from .errors import PettaError
from .results import Rows
from .space import MeTTa

__all__ = ["AsyncMeTTa", "connect"]


class AsyncMeTTa:
    """A space whose calls are awaited instead of blocking.

        async with petta.aio.connect() as am:
            await am.add(S.edge(1, 2))
            rows = await am.query(S.edge(V.a, V.b))

    Every method mirrors MeTTa's method of the same name, bounds and
    capture included; call(fn) reaches anything not mirrored by running
    fn(m) on the engine's thread. The worker thread attaches a Prolog
    engine once, so the fast calling convention holds there, the same
    pattern remote.serve() runs.
    """

    def __init__(self, space: str = "&self", *, metta: MeTTa | None = None) -> None:
        self._m = metta if metta is not None else MeTTa(space)
        self._work: "queue.Queue[tuple[Callable, MeTTa, asyncio.AbstractEventLoop, asyncio.Future] | None]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._owner = True

    @classmethod
    def _sharing(cls, metta: MeTTa, work, thread) -> "AsyncMeTTa":
        shared = cls.__new__(cls)
        shared._m = metta
        shared._work = work
        shared._thread = thread
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

    async def start(self) -> "AsyncMeTTa":
        """Start the engine thread; connect() and `async with` call this."""
        if self._thread is not None or not self._owner:
            return self
        started: asyncio.Future = asyncio.get_running_loop().create_future()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            # A persistent attached engine makes this thread first-class
            # for janus, exactly as remote.serve()'s worker: the fast
            # calling convention works here and per-call attach cost is
            # gone. Measured in the serve() round; the pattern is the
            # janus-documented one for a thread calling Prolog repeatedly.
            import petta as pkg

            pkg.janus.attach_engine()
            loop.call_soon_threadsafe(
                lambda: started.done() or started.set_result(None)
            )
            while True:
                item = self._work.get()
                if item is None:
                    pkg.janus.detach_engine()
                    return
                # Each item carries its own target space: borrowed spaces
                # from space() share this thread, not this space.
                fn, target, caller_loop, future = item
                try:
                    result = fn(target)
                except BaseException as exc:  # delivered, never swallowed
                    self._deliver(caller_loop, future, exc, failed=True)
                else:
                    self._deliver(caller_loop, future, result, failed=False)

        self._thread = threading.Thread(
            target=worker, name="petta-aio", daemon=True
        )
        self._thread.start()
        await started
        return self

    @staticmethod
    def _deliver(loop, future, payload, *, failed: bool) -> None:
        def resolve() -> None:
            if future.done():  # the awaiting task was cancelled; no receiver
                return
            if failed:
                future.set_exception(payload)
            else:
                future.set_result(payload)

        try:
            loop.call_soon_threadsafe(resolve)
        except RuntimeError:
            # The loop closed while the engine worked: the coroutine that
            # asked no longer exists, so there is nowhere to deliver to.
            pass

    async def call(self, fn: Callable[[MeTTa], Any]) -> Any:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all."""
        if self._closed:
            raise PettaError("this AsyncMeTTa is closed")
        if self._thread is None:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._work.put((fn, self._m, loop, future))
        return await future

    # ------------------------------------------------------- mirrored surface

    async def run(self, source: str, using: dict | None = None, **bounds) -> Any:
        return await self.call(lambda m: m.run(source, using, **bounds))

    async def load(self, path: str) -> list:
        return await self.call(lambda m: m.load(path))

    async def save(self, path: str) -> int:
        return await self.call(lambda m: m.save(path))

    async def add(self, *atoms: Any) -> None:
        return await self.call(lambda m: m.add(*atoms))

    async def add_table(self, head: Any, data: Any) -> int:
        return await self.call(lambda m: m.add_table(head, data))

    async def remove(self, atom: Any) -> bool:
        return await self.call(lambda m: m.remove(atom))

    async def clear(self) -> None:
        return await self.call(lambda m: m.clear())

    async def count(self) -> int:
        return await self.call(lambda m: m.count())

    async def atoms(self) -> list:
        return await self.call(lambda m: m.atoms())

    async def query(self, *patterns: Any, **options) -> Rows:
        return await self.call(lambda m: m.query(*patterns, **options))

    async def eval(self, target: Any, **bounds) -> Any:
        return await self.call(lambda m: m.eval(target, **bounds))

    async def value(self, target: Any, **bounds) -> Any:
        return await self.call(lambda m: m.value(target, **bounds))

    async def space(self, name: str) -> "AsyncMeTTa":
        """Another space through the same engine thread. The connection
        owns the thread; spaces borrow it, so closing a borrowed space is
        a no-op and closing the owner ends them all."""
        named = await self.call(lambda m: m.space(name))
        return AsyncMeTTa._sharing(named, self._work, self._thread)

    # -------------------------------------------------------------- lifecycle

    async def aclose(self) -> None:
        """Stop accepting, let queued work finish, and end the thread."""
        if self._closed:
            return
        self._closed = True
        if not self._owner or self._thread is None:
            return
        self._work.put(None)
        thread = self._thread
        await asyncio.get_running_loop().run_in_executor(None, thread.join)

    async def __aenter__(self) -> "AsyncMeTTa":
        return await self.start()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        state = "closed" if self._closed else ("live" if self._thread else "unstarted")
        return f"AsyncMeTTa({self._m.space_name!r}, {state})"


async def connect(space: str = "&self", *, metta: MeTTa | None = None) -> AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point."""
    return await AsyncMeTTa(space, metta=metta).start()
