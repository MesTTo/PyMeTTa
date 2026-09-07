"""Purpose: a recorded run, navigable in both directions and replayable.
m.record(src) runs the program under the trace with its generator pinned to a
seed, and answers a Recording: the events, the header that says what state they
were produced in, an index that makes a step backwards cost nothing, and the
two doors that turn the data back into a live execution.

The shape is rr's. rr records the nondeterministic inputs once, replays
deterministically, and reverse-executes by restoring the nearest earlier
checkpoint and running forward [source:
https://rr-project.org; O'Callahan et al., "Engineering Record and Replay for
Deployability", USENIX ATC 2017, arXiv:1705.05937]. Here the log IS the
recording, the only nondeterministic input a program has without a host call is
the random generator, and the checkpoint is the frame index: a step backwards
over recorded data costs a list lookup, and a LIVE inspection at event k costs
one replay of k events, which is `debug(at=k)`.

Guarantees:
  - a recording saves and loads round-trip: same header, same events, same
    answers [tested: test_a_recording_saves_and_loads_unchanged,
    test_a_gzipped_recording_round_trips; commit=WORKTREE]
  - replay refuses a space whose digest differs and a program that was not
    replayable, and reports the first event that diverged rather than the
    fact that something did [tested: test_replay_refuses_a_space_whose_content_differs,
    test_replay_refuses_a_program_that_reaches_the_host,
    test_replay_reports_the_first_divergent_event; commit=WORKTREE]
  - navigation is by index and by head, and an index outside the range raises
    IndexError [tested: test_navigation_walks_backwards_and_forwards,
    test_a_frame_outside_the_recording_refuses; commit=WORKTREE]
  - a frame's stack is the chain of open calls at that event, agreeing with
    the depths [tested: test_a_frames_stack_agrees_with_the_depths;
    commit=WORKTREE]
  - debug(at=k) hands back a session already stopped at the recording's k-th
    event, and refuses when the replay took another path
    [tested: test_debug_at_stops_at_that_events_term; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import os
import random
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._atom_wire import _atom_from_wire
from ._debug import debug as _open_debugger
from ._space_persistence import (
    _open_maybe_gz,
    _sync_and_replace,
    _temporary_sibling,
    serializable,
)
from ._trace import DEFAULT_MAX_EVENTS, Trace, TraceEvent, _as_source, _selected_names
from ._trace import trace as _run_traced
from ._version import __version__
from .atoms import Atom, _to_atom
from .errors import MettaError, Remedy, refusing
from .vocabularies import EffectClass, Limit

__all__ = ["Frame", "Recording", "RecordingVersionWarning", "record"]

#: What a saved recording says it is, so a file that is not one refuses by
#: name rather than by KeyError halfway through decoding it.
_FORMAT = "metta-recording"

#: The layout number of the document below, raised when a reader could no
#: longer make sense of an older file. The engine identity beside it is a
#: different question: a file this reader can parse but another engine wrote
#: WARNS, because the events may still be exactly what that program does.
_LAYOUT = 1

#: The effect class that blocks a replay. An oracleIO operation reads
#: something outside the space -- the host, a clock, a provider -- and
#: re-running it is a new reading rather than the recorded one.
_UNREPLAYABLE = EffectClass.oracleIO

#: The walk's own word for a call it could not resolve, which is unknown
#: rather than "reads the host": a variable-headed template is the commonest
#: term there is and every recursive function carries one. Read past, exactly
#: as the write guard does [source: metta/_space.py, _UNRESOLVED_OPERATION].
_UNRESOLVED = "<dynamic-operation>"


class RecordingVersionWarning(UserWarning):
    """A recording written by another engine, loaded anyway.

    The events are data and stay readable; what may not hold is that replaying
    them in THIS engine takes the same path, so the warning is at load and the
    refusal, if there is one, comes from the comparison replay makes.
    """


@dataclass(frozen=True)
class Frame:
    """One event of a recording, with where it sits and what encloses it.

    ``index`` is its position in the recording and ``seq`` the engine's own
    number for it; they agree for a recording this library made, and differ
    when a recording holds a filtered trace's prefix. The other four are the
    event's own fields, and ``stack`` is the chain of open calls at that
    moment, outermost first and ending with this event's own term, which is
    the order a Python traceback prints.
    """

    index: int
    seq: int
    time: int
    depth: int
    kind: str
    term: Atom
    answer: Atom | None
    stack: tuple[Atom, ...]

    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.kind == "exit":
            return f"[{self.index}] {indent}{self.term} = {self.answer}"
        if self.kind == "fail":
            return f"[{self.index}] {indent}-> {self.term} fails"
        return f"[{self.index}] {indent}-> {self.term}"


def _parent_chain(events: Iterable[TraceEvent]) -> tuple[int, ...]:
    """The enclosing open call of every event, by index, -1 at the top.

    ONE pass, and every entry is appended once and dropped once, so the index
    costs O(events); materialising each event's stack instead would cost
    O(events x depth) and hold a tuple per event. A stack is then the walk up
    this chain, which is the spaghetti stack every call-tree walker keeps:
    each frame points at its parent and siblings share the tail.
    """
    parents: list[int] = []
    open_at: list[int] = []
    for index, event in enumerate(events):
        del open_at[event.depth:]
        # A depth that jumps by more than one has no recorded parent at the
        # level between, which is what a FILTERED trace leaves behind: the
        # excluded call still contributed depth. The gap is a top, not a
        # crash.
        if len(open_at) < event.depth:
            open_at.extend([-1] * (event.depth - len(open_at)))
        open_at.append(index)
        parents.append(open_at[event.depth - 1] if event.depth else -1)
    return tuple(parents)


def _engine_identity(space: Any) -> dict[str, str]:
    """This library's version and the Prolog under it, as the file records it."""
    row = space.runtime.once("current_prolog_flag(version, Version)")
    return {"metta": __version__, "swi_prolog": str(row.get("Version", ""))}


def _wire_bindings(bound: Mapping[str, Any] | None) -> dict[str, Any]:
    """The named host values in force, on the wire, or a refusal to record.

    A value with no wire spelling is a live host object, and a recording that
    claimed to carry it would replay against a different object. Raising here
    would be wrong too: the run is still perfectly recordable, so the caller
    gets the recording with ``replayable`` false and the reason naming the
    binding.
    """
    encoded: dict[str, Any] = {}
    for name, value in (bound or {}).items():
        encoded[str(name)] = _to_atom(value).to_wire()
    return encoded


def _seeded_operations(space: Any) -> frozenset[str]:
    """The oracleIO operations a pinned seed makes repeat, as the engine says.

    `random-int` is oracleIO and a recording of it replays exactly, because the
    seed captured the draw; `current-time` is oracleIO and never will. The
    engine and its libraries declare which is which through
    seam:seeded_operation/1, so this reads the list rather than holding a
    second copy that goes stale when the engine grows another draw.
    """
    row = space.runtime.must("metta_py_seeded_operations(Names)")
    return frozenset(str(name) for name in row["Names"])


def _runnable_forms(space: Any, program: str) -> list[str]:
    """The `!` forms of one source, as the engine's own reader spells them.

    A recorded program is SOURCE, several forms of it, and the effect plan
    analyses one target; the reader is what turns the first into the second.
    A form's text excludes its leading `!`, which is exactly what the plan
    takes [source: extensions/python/metta/_source_forms.py, the reader's own
    contract].
    """
    row = space.runtime.must("metta_py_read_forms(Source, Forms)", Source=program)
    return [str(text) for kind, text in row["Forms"] if str(kind) == "runnable"]


def _replayability(space: Any, program: str,
                   bound: Mapping[str, Any] | None) -> tuple[bool, str | None]:
    """Whether re-running this program can reproduce the recorded events.

    Two questions, both asked before the run. The effect plan says whether the
    program reaches outside the space at all: an ``oracleIO`` operation reads
    the host, the clock or a provider, and reading it again is a new answer
    rather than the recorded one. Then the bound host values, which have to be
    re-establishable from the file.
    """
    seeded = _seeded_operations(space)
    for form in _runnable_forms(space, program):
        try:
            plan = space.effect_plan(form)
        except MettaError as refusal:
            # A form the analysis cannot translate is one replay cannot
            # promise anything about, and saying so is the whole point of the
            # field. The events are recorded either way.
            return False, f"the effect plan of ({form}) could not be read: {refusal}"
        reaching = sorted(
            name for name, effect in plan.operations
            if effect == _UNREPLAYABLE and name != _UNRESOLVED and name not in seeded
        )
        if not reaching:
            continue
        return False, (
            f"({form}) reaches {', '.join(reaching)}, whose effect class is "
            f"{_UNREPLAYABLE.value} and whose answers no seed pins: "
            f"re-running it reads the host again rather than the reading "
            f"this recording holds"
        )
    for name, value in (bound or {}).items():
        # serializable/1 is save()'s own question, and the same answer:
        # a live host object has no cross-process spelling, so a file
        # claiming to carry it would replay against a different object.
        try:
            atom = _to_atom(value)
        except (TypeError, ValueError) as refusal:
            return False, f"the bound value {name!r} is not an atom ({refusal})"
        if not serializable(atom):
            return False, (
                f"the bound value {name!r} carries a live host object, which "
                f"has no cross-process spelling, so a replay would run "
                f"against a different one"
            )
    return True, None


def _content_digest(space: Any) -> tuple[str, str | None]:
    """The space's content digest, or why there is none.

    A space a provider backs may refuse to be enumerated, and one holding a
    live host object has no cross-process spelling to digest. Neither stops the
    RUN being recorded: the events are what they are, and what is lost is the
    replay, so the refusal becomes the reason rather than the answer. It is the
    other half of the same question the effect plan asks -- a read that reaches
    outside what the recording captured.
    """
    try:
        return space.digest(), None
    except (MettaError, ValueError) as refusal:
        return "", (
            f"this space has no content digest ({refusal}), so a replay has "
            f"nothing to check the atoms it would reduce against"
        )


def _event_row(event: TraceEvent) -> list[Any]:
    """One event as the file holds it: the engine's own wire row, numbered.

    The term crosses as its WIRE rather than as its text, which costs bytes
    and buys back exactly the class of bug the tracer's own note records: read
    from text, a symbol whose spelling reads as something else came back as
    something else, and `(holds $notvar)` reloaded as a variable.
    """
    row: list[Any] = [
        event.seq, event.time, event.depth, event.kind, event.term.to_wire()
    ]
    if event.answer is not None:
        row.append(event.answer.to_wire())
    return row


def _event_from_row(row: list[Any]) -> TraceEvent:
    seq, moment, depth, kind, term, *answer = row
    return TraceEvent(
        int(seq),
        int(moment),
        int(depth),
        str(kind),
        _atom_from_wire(term),
        _atom_from_wire(answer[0]) if answer else None,
    )


@dataclass(slots=True)
class Recording:
    """A run that happened, as data you can walk, save and re-run.

    ``events`` is the trace itself and everything else is the header that says
    what state produced it: the ``program`` and the ``space`` it ran in, that
    space's ``digest``, the ``seed`` its generator was pinned to, the ``bound``
    host values in force, and the ``engine`` that ran it. ``replayable`` and
    ``reason`` are the verdict recorded at the time, because the answer can
    change afterwards and the recording's is the one that matters.

    The cursor is one position into the events, moved by ``seek``, ``back``
    and ``forward`` and read by ``position``; ``at`` reads any index without
    moving it.
    """

    program: str
    space: str
    digest: str
    seed: int
    bound: Mapping[str, Any]
    engine: Mapping[str, str]
    events: Trace
    replayable: bool
    reason: str | None
    #: The live Space this was recorded in, when there is one. A LOADED
    #: recording has none, which is why replay and debug take one.
    live: Any = field(default=None, repr=False, compare=False)
    _parents: tuple[int, ...] = field(
        default=(), init=False, repr=False, compare=False
    )
    _position: int = field(default=0, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._parents = _parent_chain(self.events)

    def __len__(self) -> int:
        """How many events the recording holds."""
        return len(self.events)

    def __repr__(self) -> str:
        cut = f", stopped={self.events.stopped.value}" if self.events.stopped else ""
        blocked = "" if self.replayable else ", not replayable"
        return (
            f"Recording({self.program!r}, {len(self.events)} events, "
            f"seed={self.seed}{cut}{blocked})"
        )

    # ---- navigation -------------------------------------------------------

    def _resolve(self, index: int, called: str) -> int:
        """One index, with Python's own negative reading, or IndexError."""
        total = len(self.events)
        resolved = index + total if index < 0 else index
        if not 0 <= resolved < total:
            msg = (
                f"{called}({index}) is outside a recording of {total} "
                f"event{'' if total == 1 else 's'}"
            )
            raise IndexError(msg)
        return resolved

    def at(self, index: int) -> Frame:
        """The frame at one index, without moving the cursor.

        A negative index counts from the end, as everywhere else in Python.
        Building the frame walks the parent chain, so it costs the event's own
        depth and nothing else.
        """
        resolved = self._resolve(index, "at")
        event = self.events[resolved]
        return Frame(
            resolved, event.seq, event.time, event.depth, event.kind,
            event.term, event.answer, self.stack(resolved),
        )

    def stack(self, index: int) -> tuple[Atom, ...]:
        """The chain of open calls at one event, outermost first.

        The last term is the event's own, so `rec.stack(k)[-1]` is what was
        reducing and `[:-1]` is what it was reducing inside.
        """
        resolved = self._resolve(index, "stack")
        terms: list[Atom] = []
        walk = resolved
        while walk >= 0:
            terms.append(self.events[walk].term)
            walk = self._parents[walk]
        terms.reverse()
        return tuple(terms)

    @property
    def position(self) -> int:
        """Where the cursor is: the index ``back`` and ``forward`` move from."""
        return self._position

    def seek(self, index: int) -> Frame:
        """Move the cursor to one index and answer the frame there."""
        frame = self.at(index)
        self._position = frame.index
        return frame

    def _step(self, to: int, called: str) -> Frame:
        """One cursor move, refusing at the ends.

        It cannot go through ``seek``: -1 there is the LAST event, Python's
        own reading of a negative index, and a `back()` at the first event
        would jump to the end instead of saying there is nothing before it.
        """
        if not 0 <= to < len(self.events):
            msg = (
                f"{called}() from event {self._position} leaves a recording "
                f"of {len(self.events)} events"
            )
            raise IndexError(msg)
        return self.seek(to)

    def back(self) -> Frame:
        """Step one event backwards and answer the frame there.

        This is the whole point of a recording: the step costs a lookup,
        because the past is data rather than a re-execution. Stepping before
        the first event raises IndexError, as reading past either end does.
        """
        return self._step(self._position - 1, "back")

    def forward(self) -> Frame:
        """Step one event forwards and answer the frame there."""
        return self._step(self._position + 1, "forward")

    def find(self, head: Any) -> tuple[Frame, ...]:
        """Every frame whose term is a call on that head, in order.

        The head is named the way every door here names one: ``S.fib``,
        ``m.fn.fib``, the string ``"fib"``, or an iterable of them for
        several. ``rec.seek(rec.find(S.fib)[0].index)`` is how a search
        becomes a position.
        """
        wanted = set(_selected_names(head, "head") or ())
        return tuple(
            self.at(index)
            for index, event in enumerate(self.events)
            if str(getattr(event.term, "head", event.term)) in wanted
        )

    # ---- the file ---------------------------------------------------------

    def document(self) -> dict[str, Any]:
        """The recording as the plain data ``save`` writes.

        Named so a caller who wants the JSON somewhere else -- a request body,
        a notebook cell, another store -- does not have to write a file to get
        it. ``save`` is this plus the atomic write.
        """
        return {
            "format": _FORMAT,
            "version": _LAYOUT,
            "engine": dict(self.engine),
            "program": self.program,
            "space": self.space,
            "digest": self.digest,
            "seed": self.seed,
            "bound": dict(self.bound),
            "replayable": self.replayable,
            "reason": self.reason,
            "stopped": None if self.events.stopped is None else self.events.stopped.value,
            "events": [_event_row(event) for event in self.events],
        }

    def save(self, path: str | os.PathLike[str]) -> int:
        """Write the recording to one file and answer how many events it holds.

        The conventional name is ``<something>.metta-rec.json``, and a name
        ending ``.gz`` is gzipped, which is the same rule ``Space.save``
        follows. The write is atomic: a temporary sibling, fsync, rename, so
        an interrupted save leaves the previous file rather than half of a new
        one.
        """
        target = Path(os.fspath(path))
        temporary = _temporary_sibling(target)
        try:
            with _open_maybe_gz(temporary, "wt") as handle:
                json.dump(self.document(), handle, separators=(",", ":"))
                handle.write("\n")
            _sync_and_replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return len(self.events)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> Recording:
        """Read a recording back, gunzipping a ``.gz`` name.

        A file written by another engine version loads and WARNS: its events
        are data and stay exactly as readable, and what the other version may
        change is whether replaying them here takes the same path, which the
        replay's own comparison reports. A file that is not a recording at all
        refuses by name.
        """
        with _open_maybe_gz(path, "rb") as handle:
            payload = handle.read()
        document = json.loads(payload.decode("utf-8"))
        if not isinstance(document, dict) or document.get("format") != _FORMAT:
            msg = (
                f"{os.fspath(path)!r} is not a MeTTa recording: a recording's "
                f"format field reads {_FORMAT!r}"
            )
            raise ValueError(msg)
        if document.get("version") != _LAYOUT:
            msg = (
                f"{os.fspath(path)!r} holds layout {document.get('version')!r} "
                f"and this reader knows {_LAYOUT}; re-record it"
            )
            raise ValueError(msg)
        engine = dict(document.get("engine") or {})
        if engine.get("metta") != __version__:
            warnings.warn(
                RecordingVersionWarning(
                    f"{os.fspath(path)!r} was recorded by metta "
                    f"{engine.get('metta')!r} and this one is {__version__!r}; "
                    f"the events load unchanged, and a replay compares them "
                    f"against what this engine does now"
                ),
                stacklevel=2,
            )
        stopped = document.get("stopped")
        events = Trace(
            (_event_from_row(row) for row in document.get("events") or ()),
            stopped=None if stopped is None else Limit(str(stopped)),
        )
        return cls(
            str(document["program"]),
            str(document["space"]),
            str(document["digest"]),
            int(document["seed"]),
            dict(document.get("bound") or {}),
            engine,
            events,
            bool(document.get("replayable", False)),
            document.get("reason"),
        )

    # ---- back to a live execution -----------------------------------------

    def _target(self, space: Any, called: str) -> Any:
        if space is not None:
            return space
        if self.live is not None:
            return self.live
        msg = (
            f"this recording was loaded from a file, so it has no live space "
            f"to {called} in; pass one, as {called}(m)"
        )
        raise refusing(
            MettaError(msg),
            remedy=Remedy(
                f"{called} takes the space to run in",
                "quickfix",
                "prose",
                python=f"rec.{called}(m)",
            ),
        )

    def _require_replayable(self, called: str) -> None:
        if self.replayable:
            return
        msg = (
            f"this recording is not replayable, so {called} would run a "
            f"different execution: {self.reason}"
        )
        raise refusing(
            MettaError(msg),
            remedy=Remedy(
                "read the recorded events instead of re-running them",
                "refactor",
                "prose",
                python="for frame in (rec.at(k) for k in range(len(rec))): ...",
            ),
        )

    def _cold(self, space: Any) -> None:
        """Put the target engine back to the state a first run starts from.

        The digest pins a space's ATOMS and the seed pins the draws; this is
        the third piece of the state a recorded run began in. A library that
        answers from something it derived earlier -- a memo, a table -- takes a
        shorter path the second time and produces a shorter event stream for
        the same answers: `!(fib 6)` records 22 events and replays 2 in the
        engine that recorded it, every call after the first served from the
        cache [measured 2026-09-07]. Asking every library to forget makes each
        replay start where the recording did, and makes repeated seeks agree
        with each other, which is what `debug(at=k)` needs to be usable at all.

        The decisions survive: a function the automatic memo chose stays
        chosen and caches again from its next call. It is the ENGINE's derived
        answers, not this space's: the reset is total for the reason the
        tracer's teardown is, that a reset which is sometimes partial is a
        silent divergence, and a caller replaying a recorded run is asking for
        the engine as cold as it can be made.
        """
        space.runtime.do_must("metta_py_forget_derived")

    def _require_same_space(self, space: Any, called: str) -> None:
        digest = space.digest()
        if digest == self.digest:
            return
        msg = (
            f"{called} needs the space the recording was made over: this one "
            f"digests {digest[:12]}... where the recording holds "
            f"{self.digest[:12]}..., so the program would reduce against "
            f"different atoms"
        )
        raise refusing(
            MettaError(msg),
            remedy=Remedy(
                "load the recorded content into the space first",
                "quickfix",
                "prose",
                python="m.load(path)  # the atoms the recording digests",
            ),
        )

    def replay(self, space: Any = None) -> Trace:
        """Re-run the program under the recorded seed and compare, event by event.

        Answers the replayed Trace when every event matches, and raises naming
        the FIRST one that did not, because "something diverged" sends a reader
        through the whole log to find out what.

        ``time`` is the one field not compared: it is when the event happened,
        and no two runs agree on that. Everything else is: the sequence, the
        depth, the port, the term and the answer.

        The target engine is put back to a first run's state before the
        program runs: every library is asked to forget what it derived
        earlier, because a memo answers the second run in fewer steps than the
        first and the recording holds the first. What that cannot restore is a
        cache the RECORDING itself ran under, so a recording made in an engine
        that had already computed part of the program replays longer than it
        recorded and says so.
        """
        target = self._target(space, "replay")
        self._require_replayable("replay")
        self._require_same_space(target, "replay")
        self._cold(target)
        # A COMPLETE recording is replayed with one event of headroom, so a
        # replay that runs longer shows as a length difference instead of
        # being cut to fit; a recording a bound already CUT is replayed to
        # exactly its own length, which is the same prefix under the same
        # bound.
        if not self.events:
            allowed = DEFAULT_MAX_EVENTS
        elif self.events.stopped is None:
            allowed = len(self.events) + 1
        else:
            allowed = len(self.events)
        replayed = _run_traced(
            target, self.program, max_events=allowed, seed=self.seed,
        )
        self._compare(replayed)
        return replayed

    def _compare(self, replayed: Trace) -> None:
        for index, recorded in enumerate(self.events):
            if index >= len(replayed):
                msg = (
                    f"the replay stopped after {len(replayed)} events where "
                    f"the recording holds {len(self.events)}; its next event "
                    f"is {recorded.kind} {recorded.term}"
                )
                raise MettaError(msg)
            again = replayed[index]
            if (recorded.seq, recorded.depth, recorded.kind) == (
                again.seq, again.depth, again.kind
            ) and recorded.term == again.term and recorded.answer == again.answer:
                continue
            msg = (
                f"the replay diverged at event {index}: the recording holds "
                f"{recorded.kind} {recorded.term}"
                f"{'' if recorded.answer is None else f' = {recorded.answer}'} "
                f"and the replay produced {again.kind} {again.term}"
                f"{'' if again.answer is None else f' = {again.answer}'}"
            )
            raise MettaError(msg)
        if self.events.stopped is None and len(replayed) > len(self.events):
            extra = replayed[len(self.events)]
            msg = (
                f"the replay ran past the recording's {len(self.events)} "
                f"events, reaching {extra.kind} {extra.term}"
            )
            raise MettaError(msg)

    def debug(self, space: Any = None, *, at: int) -> Any:
        """Replay to the recording's k-th event and hand back a live session there.

        This is the recording's other direction: ``at(k)`` reads what happened
        at event k, and this one puts the program back at that moment with its
        bindings live, so `d.stop` is that event and stepping carries on from
        it. The cost is one replay of k events, which is the checkpoint-and-run-
        forward that reverse execution is built on everywhere it exists.

        It verifies that it landed on the recorded event and refuses otherwise,
        so a session that is not where you asked for says so rather than
        letting you read the wrong frame.
        """
        # The refusal a whole recording carries comes FIRST: an unreplayable
        # recording cannot be seeked into at any index, and answering
        # IndexError for its empty event list would name the wrong problem.
        self._require_replayable("debug")
        frame = self.at(at)
        target = self._target(space, "debug")
        self._require_same_space(target, "debug")
        self._cold(target)
        session = _open_debugger(target, self.program, at=frame.seq)
        stop = next(session, None)
        if stop is None or (stop.seq, stop.kind) != (frame.seq, frame.kind) \
                or stop.term != frame.term:
            session.close()
            reached = "ran to the end" if stop is None else f"stopped at {stop}"
            msg = (
                f"replaying to event {frame.index} took a different path: the "
                f"recording holds {frame.kind} {frame.term} and the replay "
                f"{reached}. The replay starts from a first run's state, so a "
                f"recording made in an engine that had ALREADY computed part "
                f"of this program cannot be seeked into; record it again from "
                f"a cold engine"
            )
            raise refusing(
                MettaError(msg),
                remedy=Remedy(
                    "record the run from a first-run state",
                    "quickfix",
                    "prose",
                    python='m.record(src)  # in an engine that has not run it',
                ),
            )
        return session


def record(space: Any, source: Atom | str, *,
           seed: int | None = None,
           max_events: int | None = None,
           timeout: float | None = None,
           inferences: int | None = None,
           bound: Mapping[str, Any] | None = None) -> Recording:
    """Run a term, or source, and keep the whole run as data.

    The rung below is ``m.trace``, which answers the events alone; a Recording
    is those events plus the state they were produced in, which is what makes
    them re-runnable rather than only readable.

    A recorded run ALWAYS has a seed, minted when you do not name one, because
    a replay that cannot reproduce the draws is not a replay. The generator is
    restored afterwards, so the engine is left where it was; the MeTTa spelling
    of the same scope is ``(with-seed S expr)``.

    max_events bounds the RECORDING and timeout and inferences bound the RUN,
    exactly as they do on ``trace``; a recording cut by one of them says so
    through ``rec.events.stopped`` and replays to the same length.
    """
    program = _as_source(source)
    # Minted here rather than engine-side so the recording's own header is the
    # only place the number lives: a seed the engine chose would have to be
    # reported back out of the trace door to be recorded at all.
    chosen = (
        random.randrange(1, 2**31 - 1)  # noqa: S311  -- a replay seed reproduces a run; nothing here is a secret
        if seed is None
        else int(seed)
    )
    if chosen < 0:
        msg = f"a seed is a non-negative integer, not {seed!r}"
        raise ValueError(msg)
    scoped = dict(bound or {})
    replayable, reason = _replayability(space, program, scoped)
    digest, digest_refusal = _content_digest(space)
    if digest_refusal is not None:
        replayable, reason = False, digest_refusal
    events = _run_traced(
        space, program, max_events=max_events,
        timeout=timeout, inferences=inferences, seed=chosen,
    )
    return Recording(
        program,
        space.name,
        digest,
        chosen,
        _wire_bindings(scoped) if replayable else {},
        _engine_identity(space),
        events,
        replayable,
        reason,
        live=space,
    )
