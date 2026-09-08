"""Purpose: breakpoints, suspension, stepping and resume as Python objects.
m.debug(term, on=...) answers a Debugger: iterating it runs the program until
a breakpoint, the loop body is where the program is SUSPENDED, and leaving the
body resumes it. The program is a real run, writes included, held inside an
SWI engine that the host steps.
Guarantees:
  - a scope closes both unstarted and suspended sessions and retires their
    tracing wrappers [tested:
    test_scope_closes_held_debuggers_and_retires_their_wrappers;
    commit=c6e1198c490a824b96f6fc6e1c0622a542917024].
  - a breakpoint suspends the program and the loop body observes it, then
    resuming carries the same execution on to the next one [tested:
    test_a_breakpoint_suspends_the_program_and_resuming_carries_it_on;
    commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f]
  - step() stops at the very next reduction, breakpoint or not, and resume()
    puts the session back on breakpoints [tested: test_step_stops_at_the_next_reduction;
    commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f]
  - breakpoints are a live set: one added while the program is suspended
    stops it, and one removed stops stopping it [tested:
    test_breakpoints_can_be_changed_while_the_program_is_suspended;
    commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f]
  - the session's wrappers come off at close, so a later trace or run is
    untouched, and a dropped Debugger is reaped by its finalizer [tested:
    test_a_debug_session_leaves_the_engine_as_it_found_it; commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f]
  - inferences bound the WHOLE session cumulatively, so a resume that would
    never reach another breakpoint stops [tested:
    test_an_inference_bound_stops_a_resume_that_would_never_return;
    commit=39dd4c9014bf8c38d78df8c8fdc9c114b372dc1f]
  - at= stops at the event with that sequence number, the same numbering a
    Recording indexes by, and a negative one refuses rather than running to
    the end [tested: test_a_count_breakpoint_stops_at_that_event,
    test_a_negative_count_breakpoint_refuses; commit=e54c3654b9e0d3d040560d12c105a54303f63af7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import logging
import weakref
from dataclasses import dataclass
from typing import Any

from . import _scope
from ._atom_wire import _atom_from_wire
from ._space_execution import _controlled_run
from ._trace import _as_source, _selected_names
from .atoms import Atom
from .errors import EngineError, MettaError

__all__ = ["Debugger", "Stop", "debug"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stop:
    """Where the program is, halted.

    The term entering or leaving reduction, its nesting depth, the answer on
    an exit, and the seq and time that number and date it: the same six fields
    a TraceEvent carries, because it is the same event; what differs is that
    the program is still running underneath this one and will carry on when
    the loop body ends. The seq is the one a recording of the same program
    indexes by, which is what ``at=`` seeks to. ``function`` is the head's
    name, which is what a breakpoint is named after.
    """

    seq: int
    time: int
    depth: int
    kind: str
    term: Atom
    answer: Atom | None

    @property
    def function(self) -> str:
        """The head this stop is inside, as the engine spells it."""
        return str(getattr(self.term, "head", self.term))

    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.kind == "exit":
            return f"{indent}{self.term} = {self.answer}"
        if self.kind == "fail":
            return f"{indent}-> {self.term} fails"
        return f"{indent}-> {self.term}"


class Debugger:
    """A suspended program, stepped from Python.

    Iterate it and each answer is a Stop: the program is halted there, and
    the loop body is where you look at it. Ending the body resumes the same
    execution. That division is CPython's own bdb, where the stop callback is
    the suspension, ``set_step``/``set_continue`` choose how the program goes
    on, and returning from the callback is what resumes it
    [source: https://github.com/python/cpython/blob/3.14/Lib/bdb.py].

    Underneath, the program runs inside an SWI engine and each stop is an
    ``engine_yield/1`` from inside the reduction, which is the one mechanism
    that returns control from deep in a running goal and leaves it resumable
    [source: https://www.swi-prolog.org/pldoc/man?predicate=engine_yield/1].
    A blocking callback, the shape bdb and SWI's own debug adapter use, is
    not available across janus: its query iterator is not opened for
    yielding, so a callback would hold a thread inside the engine.
    """

    __slots__ = (
        "__weakref__",
        "_answers",
        "_closed",
        "_finalizer",
        "_handle",
        "_mode",
        "_rt",
        "_started",
        "_stop",
        "breakpoints",
    )

    def __init__(self, space, source: Atom | str, armed: list[str], inferences: int,
                 at: int = -1) -> None:
        #: The armed function names, as the engine spells them, and a live
        #: set: what it holds when the program resumes is what stops it next.
        #: on= is the door that takes a symbol, a bound function or a string
        #: and answers these; adding one here is the rung below it.
        self.breakpoints: set[str] = set(armed)
        self._rt = space.runtime
        self._mode = "run"
        self._started = False
        self._closed = False
        self._stop: Stop | None = None
        self._answers: list | None = None
        self._handle = _controlled_run(
            space.runtime,
            "metta_py_debug_open",
            [_as_source(source), space.name, sorted(self.breakpoints), inferences,
             at],
            None,
        )
        # The last guard, not the contract: a Debugger dropped without
        # closing would leave the tracer's wrappers on every compiled
        # function and refuse the next session, so the engine is reaped from
        # whichever thread collection runs on.
        self._finalizer = weakref.finalize(self, self._reap, self._rt, self._handle)
        try:
            _scope.own("cleanup", self.close)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _reap(runtime, handle) -> None:
        try:
            runtime.do("metta_py_debug_close", handle)
        except EngineError:
            # A finalizer has no caller; close() still reports failures.
            logger.debug("debugger finalization found an unavailable engine", exc_info=True)

    def __iter__(self):
        return self

    def __next__(self) -> Stop:
        """Advance the program and answer where it stopped.

        The first call starts it; every later one resumes the execution the
        previous Stop suspended, under whatever mode and breakpoints are set
        now. The program finishing is ordinary iterator exhaustion, and its
        answers are on ``answers`` afterwards.
        """
        if self._closed:
            # Not exhaustion: a closed session ending a for-loop quietly would
            # look exactly like a program that finished, which is the one
            # thing a debugger must not confuse.
            msg = "this debug session is closed"
            raise MettaError(msg)
        if self._answers is not None:
            raise StopIteration
        if self._started:
            record = self._rt.apply_must(
                "metta_py_debug_resume",
                self._handle,
                self._mode,
                sorted(self.breakpoints),
            )
        else:
            self._started = True
            record = self._rt.apply_must("metta_py_debug_next", self._handle)
        return self._read(record)

    def _read(self, record) -> Stop:
        seq, moment, depth, kind, *rest = record
        if str(kind) == "done":
            self._answers = [
                [_atom_from_wire(answer) for answer in group] for group in (rest[0] or [])
            ]
            raise StopIteration
        if str(kind) == "failed":
            msg = "the debugged program failed rather than answering"
            raise EngineError(msg)
        # Every resume is one advance: a mode chosen at a stop applies to the
        # next one and no further, which is set_step's own contract.
        self._mode = "run"
        self._stop = Stop(
            int(seq),
            int(moment),
            int(depth),
            str(kind),
            _atom_from_wire(rest[0]),
            _atom_from_wire(rest[1]) if len(rest) > 1 else None,
        )
        return self._stop

    def step(self) -> None:
        """Stop at the very next reduction, breakpoint or not.

        The granularity is a reduction, which is what this engine has frames
        of: a call entering a compiled MeTTa function, or its matching exit.
        The mode lasts one advance, so a loop that steps every time walks the
        program and one that steps once returns to breakpoints.
        """
        self._mode = "step"

    def resume(self) -> None:
        """Run on to the next breakpoint, cancelling a step() at this stop.

        Running on is what a Debugger does anyway, so this matters only
        where step() was already chosen and the caller changed its mind.
        """
        self._mode = "run"

    @property
    def stop(self) -> Stop | None:
        """Where the program is suspended now, or None before it has started.

        The same object the last advance answered, kept because a session
        opened already stopped -- which is what `at=` and
        `Recording.debug(at=k)` produce -- has nowhere else to say where it
        landed, and because a helper handed the Debugger can ask without
        advancing it.
        """
        return self._stop

    @property
    def answers(self) -> list:
        """The answer groups the program produced, once it has finished.

        Absent is not None: asking before the program has run to the end is a
        question with no answer yet, and saying so is more use than an empty
        list that reads as "it answered nothing".
        """
        if self._answers is None:
            msg = (
                "the debugged program has not finished; iterate the Debugger "
                "to the end, or call run() to let it finish"
            )
            raise EngineError(msg)
        return self._answers

    @property
    def finished(self) -> bool:
        """Whether the program ran to the end."""
        return self._answers is not None

    def run(self) -> list:
        """Let the program finish and answer what it produced.

        Every remaining breakpoint is dropped, so this is one advance to the
        end however many were armed.
        """
        self.breakpoints.clear()
        self.resume()
        while not self.finished:
            next(self, None)
        return self.answers

    def close(self) -> None:
        """End the session, abandoning the program where it stands.

        The engine's wrappers come off, so the next trace or debug session
        can run. Closing twice is not an error.
        """
        if self._closed:
            return
        self._rt.do("metta_py_debug_close", self._handle)
        self._closed = True
        if self._finalizer is not None:
            self._finalizer.detach()

    def __enter__(self):
        return self

    def __exit__(self, *_exception) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self._closed else ("finished" if self.finished else "suspended")
        return f"Debugger({state}, breakpoints={sorted(self.breakpoints)})"


def debug(space, source: Atom | str, *, on: Any = None, inferences: int | None = None,
          at: int | None = None) -> Debugger:
    """Run a term, or source, under breakpoints.

    on= names the functions that stop the program, the way every door here
    names a head: ``on=[S.double]``, ``on=m.fn.double`` or ``on="double"``.
    Naming none runs the program to the end in one advance, which is the
    honest reading of a debugger with no breakpoints set.

        with m.debug(S.quad(3), on=[S.double]) as d:
            for stop in d:
                print(stop)          # the program is suspended here
                if stop.depth > 2:
                    d.step()         # and this is how it goes on
            print(d.answers)

    inferences bounds the WHOLE session cumulatively, so a resume that would
    never reach another breakpoint stops with the ordinary limit error rather
    than running forever. There is no timeout, deliberately: a session is
    suspended by design and a clock would run while a person reads a stop.

    at= is the third kind of breakpoint: it stops at the event with that
    sequence number, counting reductions from 0 the way a Recording numbers
    them, so `m.debug(src, at=200)` is "put me where event 200 is". It is what
    `Recording.debug(at=k)` runs, and it fires once; the session then behaves
    like any other, on whatever `on=` named.

    What is debugged executes for real, writes included, and inherits the
    caller's scope, so `with m.speculative():` around the session discards
    what it wrote.
    """
    if at is not None and at < 0:
        msg = f"at= counts events from 0, so it cannot be {at!r}"
        raise ValueError(msg)
    return Debugger(
        space,
        source,
        _selected_names(on, "on") or [],
        -1 if inferences is None else int(inferences),
        -1 if at is None else int(at),
    )
