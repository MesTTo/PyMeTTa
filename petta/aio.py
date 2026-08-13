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

from .errors import Interrupted, PettaError
from .results import Rows
from .space import MeTTa

__all__ = ["AsyncMeTTa", "connect"]


class _Request:
    __slots__ = ("fn", "target", "loop", "future", "abandoned")

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
        self.work: "queue.Queue[_Request | None]" = queue.Queue()
        self.thread: threading.Thread | None = None
        self._transition = threading.Lock()
        self._current: _Request | None = None
        self._swi_thread: Any = None

    async def start(self) -> None:
        if self.thread is not None:
            return
        loop = asyncio.get_running_loop()
        started: asyncio.Future = loop.create_future()

        def worker() -> None:
            # A persistent attached engine makes this thread first-class
            # for janus, the same pattern remote.serve()'s worker runs:
            # the fast calling convention holds here and per-call attach
            # cost is gone. janus.engine() names this engine to
            # thread_signal, the address interrupt() throws at; a startup
            # failure is delivered to the awaiting start(), never hung on.
            import petta as pkg

            try:
                pkg.janus.attach_engine()
                self._swi_thread = pkg.janus.engine()
            except BaseException as exc:
                # Bind to an ordinary local: Python deletes the except
                # target when the block exits, and the deferred lambda
                # would find the name unbound instead of the exception.
                failure = exc
                loop.call_soon_threadsafe(
                    lambda: started.done() or started.set_exception(failure)
                )
                return
            loop.call_soon_threadsafe(
                lambda: started.done() or started.set_result(None)
            )
            while True:
                request = self.work.get()
                if request is None:
                    pkg.janus.detach_engine()
                    return
                if request.abandoned.is_set():
                    continue  # cancelled while queued: never runs
                with self._transition:
                    self._current = request
                try:
                    result = request.fn(request.target)
                except BaseException as exc:  # delivered, never swallowed
                    outcome, failed = exc, True
                else:
                    outcome, failed = result, False
                finally:
                    with self._transition:
                        self._current = None
                        self._drain(pkg)
                _deliver(request, outcome, failed=failed)

        self.thread = threading.Thread(target=worker, name="petta-aio", daemon=True)
        self.thread.start()
        await started

    def _drain(self, pkg) -> None:
        # One no-op engine call: a thread_signal throw that raced the end
        # of its goal fires here, inside the transition lock, and is
        # discarded as the stale stop it is.
        try:
            pkg.janus.query_once("true")
        except Exception:
            pass

    def interrupt_if_running(self, request: _Request | None) -> bool:
        """Signal the engine thread if `request` is the one running now,
        or if anything is running when request is None. Answers whether a
        signal was sent."""
        import petta as pkg

        with self._transition:
            current = self._current
            if current is None or (request is not None and current is not request):
                return False
            # query_once is safe from a bare foreign thread (the loop's),
            # and this bypasses the runtime lock on purpose: the running
            # goal holds that lock, and the signal is how it lets go.
            pkg.janus.query_once(
                "thread_signal(T, throw(petta_py_interrupted))",
                {"T": self._swi_thread},
            )
            return True

    def close_soon(self) -> None:
        self.work.put(None)


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
        pass


class AsyncMeTTa:
    """A space whose calls are awaited instead of blocking.

        async with petta.aio.connect() as am:
            await am.add(S.edge(1, 2))
            rows = await am.query(S.edge(V.a, V.b))

    Every method mirrors MeTTa's method of the same name, bounds and
    capture included; call(fn) reaches anything not mirrored by running
    fn(m) on the engine's thread. interrupt() stops the evaluation the
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
    def _sharing(cls, metta: MeTTa, worker: _EngineThread) -> "AsyncMeTTa":
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

    async def start(self) -> "AsyncMeTTa":
        """Start the engine thread; connect() and `async with` call this."""
        if self._owner:
            await self._worker.start()
        return self

    async def call(self, fn: Callable[[MeTTa], Any]) -> Any:
        """Run fn(m) on the engine's thread and await its result: the
        escape hatch to the entire synchronous surface, subscriptions,
        derivations, stats blocks and all."""
        if self._closed:
            raise PettaError("this AsyncMeTTa is closed")
        if self._worker.thread is None:
            await self.start()
        loop = asyncio.get_running_loop()
        request = _Request(fn, self._m, loop, loop.create_future())
        self._worker.work.put(request)
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
        return AsyncMeTTa._sharing(named, self._worker)

    # -------------------------------------------------------------- lifecycle

    async def aclose(self) -> None:
        """Stop accepting, let queued work finish, and end the thread."""
        if self._closed:
            return
        self._closed = True
        if not self._owner or self._worker.thread is None:
            return
        self._worker.close_soon()
        thread = self._worker.thread
        await asyncio.get_running_loop().run_in_executor(None, thread.join)

    async def __aenter__(self) -> "AsyncMeTTa":
        return await self.start()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        state = (
            "closed"
            if self._closed
            else ("live" if self._worker.thread else "unstarted")
        )
        return f"AsyncMeTTa({self._m.space_name!r}, {state})"


async def connect(space: str = "&self", *, metta: MeTTa | None = None) -> AsyncMeTTa:
    """An AsyncMeTTa with its engine thread already running, aiosqlite's
    own naming for the entry point."""
    return await AsyncMeTTa(space, metta=metta).start()
