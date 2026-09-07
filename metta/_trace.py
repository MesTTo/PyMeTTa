"""Purpose: the reduction trace as Python objects. m.trace(term) runs
that term with every compiled MeTTa function wrapped engine-side, and
answers TraceEvent records: a call carries the term entering reduction
at its nesting depth, the matching exit carries the answer, and a fail
carries a reduction that answered nothing. Tracing wraps and unwraps per
run, so it costs nothing when off; what is traced executes for real,
writes included, exactly like a run.
Guarantees:
  - every event carries its own seq and the wall nanoseconds since the run
    began, and a reduction reaches exactly one of exit, fail, or neither
    when a bound cut it [tested: test_events_carry_a_sequence_and_a_time,
    test_a_reduction_that_answers_nothing_records_a_fail_event;
    commit=e54c3654b9e0d3d040560d12c105a54303f63af7]
  - a memoised head records the calls its cache answers, so a recording of a
    memoised program is not empty [tested:
    test_a_memoised_head_records_the_calls_its_cache_answers; commit=e54c3654b9e0d3d040560d12c105a54303f63af7]
  - named filters select events before recording bounds without changing
    execution depth [tested: test_trace_filter_preserves_depth_and_budget;
    commit=504f8dddfa890ced97e795a13ab10e239b1de2ce]
  - a term and the source that spells it trace identically, so trace accepts
    the same input forms as every other evaluation method
    [tested test_trace_takes_the_term_every_other_door_takes]
  - traced source keeps run()'s real-write semantics while inheriting the
    same speculative execution fence [tested:
    test_every_public_execution_door_honours_speculative_policy;
    commit=1262dd20ada9d5c799d9bdc4bdf5d2b859ca7a98]
  - timeout and inferences bound the traced RUN, per call and through the
    scoped m.limits() default, independently of the max_events recording bound
    [tested: test_a_run_bound_stops_a_trace_the_way_it_stops_a_run;
    commit=73f47d27edae99e0c7fd35481040ce2d127bce76]
  - every bound answers the prefix it recorded and names itself in `stopped`,
    so a caller told a trace was cut can tell which bound to raise
    [tested: test_a_run_bound_keeps_the_events_it_recorded,
    test_each_bound_answers_its_prefix_and_names_itself]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ._atom_wire import _atom_from_wire
from ._space_execution import _controlled_run
from ._space_objects import _limits
from .atoms import Atom, Symbol, _to_atom
from .vocabularies import Limit

__all__ = ["TraceEvent", "trace"]


@dataclass(frozen=True)
class TraceEvent:
    """One step of a reduction.

    ``seq`` numbers the events of one trace from 0 and ``time`` is the wall
    nanoseconds since the run began, so an event says both where it is in the
    order and how far into the run it happened. ``depth`` is the nesting level,
    ``term`` is what reduced, and ``answer`` carries the exit's result.

    ``kind`` is the port, and a reduction reaches exactly one of three
    outcomes: ``exit`` once per answer, ``fail`` when it answered nothing, or
    neither when a bound cut the run before it finished. ``answer`` is None on
    every port but ``exit``.
    """

    seq: int
    #: Excluded from equality, because it is WHEN the step happened and not
    #: WHICH step it is: two runs of the same program produce the same
    #: reduction at different moments, and an event that carried the clock
    #: into its identity would make two traces of one program unequal and
    #: every real difference between them invisible behind that. Every other
    #: field counts, `seq` included, so a trace and a differently filtered
    #: one are not equal. `Recording.replay` compares the same way.
    time: int = field(compare=False)
    depth: int
    kind: str
    term: Atom
    answer: Atom | None

    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.kind == "exit":
            return f"{indent}{self.term} = {self.answer}"
        if self.kind == "fail":
            return f"{indent}-> {self.term} fails"
        return f"{indent}-> {self.term}"


def _selected_names(value: Any, parameter: str) -> list[str] | None:
    """The function names a door was given, as the engine spells them.

    None is "not restricted", which each door reads its own way: a trace
    records every function and a debug session arms no breakpoint. A list is
    the exact selection, empty included.

    Every way this surface names a head is accepted, because a name comes
    from its factory rather than from a string: ``S.double``, ``fn.car_atom``
    and ``m.fn.double`` all mention as their own head symbol through
    ``__metta__``, and a plain string stays the exact-head escape hatch.
    Anything that is not one head refuses by name rather than quietly
    selecting nothing.
    """
    if value is None:
        return None
    if isinstance(value, (Symbol, str)) or hasattr(value, "__metta__"):
        items = [value]
    elif isinstance(value, Iterable) and not isinstance(value, Atom):
        items = list(value)
    else:
        msg = (
            f"{parameter} must be a function Symbol, name string, "
            f"or iterable of names"
        )
        raise TypeError(msg)
    selected = []
    for item in items:
        if isinstance(item, str):
            spelling = item
        else:
            atom = _to_atom(item) if isinstance(item, Atom) or hasattr(item, "__metta__") else None
            if not isinstance(atom, Symbol):
                msg = f"{parameter} members must be function Symbols or name strings"
                raise TypeError(msg)
            spelling = atom.name
        if not spelling:
            msg = f"{parameter} names must be nonempty; use [] to select none"
            raise ValueError(msg)
        selected.append(spelling)
    return selected


def _as_source(what: Atom | str) -> str:
    """The trace's own argument, as the source the engine's tracer takes.

    An ATOM is the ordinary spelling everywhere else on this surface,
    `m.answers(S.fib(10))` rather than `m.answers("!(fib 10)")`, and
    trace once took only text, forcing callers to rewrite a term as source just
    to inspect its reduction. The tracer runs
    SOURCE, so a term is written and prefixed with the `!` that makes it
    a runnable form; `str(Atom)` is the writer the whole surface prints
    through, which is why `.source()` on a definition reads back as MeTTa.
    A string is passed through untouched, `!` included or not, so every
    call written before this still means what it meant.
    """
    return what if isinstance(what, str) else f"!{what}"


#: The bound an unqualified trace carries. An event costs the size of its
#: term and nothing bounds that, so max_events is a count against an unbounded
#: per-event cost: 10,000 events of
#: examples/ch22-a-reasoner-you-can-serve/22-03-search/02-tilepuzzle.metta peak
#: 0.26GB, and a downstream renderer measured 50,000 at 5.77GB, 100,000 above
#: 14GB, and six concurrent renders taking a 60GB machine to 2GB free with the
#: 1,000,000 this was through 2026-09-03. A default has to be survivable on an
#: ordinary machine; asking for more is one argument, and the result says when
#: it was cut.
DEFAULT_MAX_EVENTS = 10_000

#: What the shim reads as "no bound" in each of the three positions its own
#: guard takes, seconds, inferences and stack bytes.
_NO_BOUND = (-1.0, -1, -1)

#: The fourth run control the trace door takes beside those three: the seed the
#: run's generator is pinned to, or -1 for the generator the engine already had.
#: Negative is the same no-bound sentinel the three bounds use.
_NO_SEED = -1


class Trace(list):
    """The events, and which bound stopped the recording early.

    A list, because that is what a trace IS and every consumer wants to
    iterate it, index it and take its length. `stopped` is the one thing a
    plain list cannot say, and it has to be said: the honest answer to "trace
    this if it is cheap" is a prefix that admits to being one.

    It names the bound rather than raising a flag because the five bounds
    have five remedies, and a caller told only that something cut the trace
    acts on the wrong one: raising `max_events` after `Limit.memory` stopped
    a trace returns the same prefix again, and raising it after
    `Limit.inferences` runs the same program into the same wall. `truncated`
    stays as the yes-or-no reading of the same fact.
    """

    __slots__ = ("stopped",)

    def __init__(self, events=(), *, stopped: Limit | None = None) -> None:
        super().__init__(events)
        self.stopped = stopped

    @property
    def truncated(self) -> bool:
        """Whether these events are a prefix, whichever bound cut them."""
        return self.stopped is not None

    def __repr__(self) -> str:
        cut = f", stopped={self.stopped.value}" if self.stopped else ""
        return f"Trace({len(self)} events{cut})"


def trace(space, source: Atom | str,
          max_events: int | None = None,
          *,
          filter: Symbol | str | Iterable[Symbol | str] | None = None,  # noqa: A002 -- public trace selector
          timeout: float | None = None,
          inferences: int | None = None,
          seed: int | None = None) -> Trace:
    """Run a term, or source, in this space under the engine's reduction trace.

    filter selects exact function names before recording; None selects all
    and an empty iterable selects none. Excluded calls still contribute depth
    and execute normally, including their writes.

    max_events bounds the RECORDING. timeout, inferences and stack bound the
    RUN, the same triple every evaluating door takes and the same scoped
    `m.limits()` default behind them. The bounds are independent because they
    stop different things: a program can retire millions of inferences inside
    a handful of recorded events, and through 0.7.1 this door passed no limits
    at all, so `with m.limits(inferences=100)` let a traced program run
    209,322 of them to completion
    [measured 2026-09-04, `!(loop 2000)` at inferences=100: run stopped at
    1,685 with InferenceLimitError, trace finished].

    Whichever one stops it, the events already recorded are ANSWERED and
    `stopped` names the bound. Discarding them was the whole shape 0.7.0
    removed for the recording bound and the run bounds still had: measured
    2026-09-04 on 06-peano.metta's own head, a 2,000,000-inference limit took
    a 10,000-event trace to an InferenceLimitError and nothing else, and the
    renderer reading it drew 4 frames where the events give 302.

    seed pins the run's random generator and restores whatever state was in
    force afterwards, so a traced run's draws come back the same. It is the
    fourth run control, not a bound, and `record` is the door that always
    sets it; the MeTTa spelling of the same scope is `(with-seed S expr)`.
    """
    # None means unspecified, and the number lives here alone: metta._space
    # may not import this module (import-linter, "the facade does not import
    # its satellites"), so a default spelled in the facade would be a second
    # copy of it.
    if max_events is None:
        max_events = DEFAULT_MAX_EVENTS
    if max_events <= 0:
        msg = f"max_events must be positive, got {max_events!r}"
        raise ValueError(
            msg
        )
    selected = _selected_names(filter, "filter")
    request: int | list = (
        int(max_events) if selected is None else [int(max_events), selected]
    )
    # The bounds ride INSIDE the door as an argument rather than being handed
    # to _controlled_run, which would wrap the whole door: the trace's answer
    # costs seven times its run to encode, so a budget spent around the door
    # is spent on the encoding and the events go. _NO_BOUND is the shim's own
    # -1 sentinel triple, which is what an unbounded call sends.
    stopped, records = _controlled_run(
        space.runtime,
        "metta_py_trace",
        [
            _as_source(source),
            space.name,
            request,
            [*(_limits(timeout, inferences) or _NO_BOUND),
             _NO_SEED if seed is None else int(seed)],
        ],
        None,
    )
    return _recorded(stopped, records)


def _events(records) -> list[TraceEvent]:
    """The wire's event rows as TraceEvents.

    Events cross as terms on the ordinary wire. Read back from their own text, a
    symbol whose spelling reads as something else arrived as something else:
    `(holds $notvar)` traced as a variable while run answered the symbol, and a
    tab inside a symbol split the record.
    """
    events = []
    for record in records or []:
        seq, moment, depth, kind, term, *answer = record
        events.append(
            TraceEvent(
                int(seq),
                int(moment),
                int(depth),
                str(kind),
                _atom_from_wire(term),
                _atom_from_wire(answer[0]) if answer else None,
            )
        )
    return events


def _recorded(stopped, records) -> Trace:
    """One recording session's answer: its events and the bound that cut them.

    The wire carries the bound's own word, or `false` when the run finished. An
    unknown word is a `Limit()` ValueError rather than a silently
    complete-looking trace, which is the failure a bool could not have. The
    trace door and the held observe session both end this way, so the reading is
    written once.
    """
    stopped = str(stopped)
    return Trace(_events(records), stopped=None if stopped == "false" else Limit(stopped))
