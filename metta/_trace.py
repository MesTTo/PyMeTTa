"""Purpose: the reduction trace as Python objects. m.trace(term) runs
that term with every compiled MeTTa function wrapped engine-side, and
answers TraceEvent records: a call carries the term entering reduction
at its nesting depth, the matching exit carries the answer, and a call
with no exit is a reduction that failed. Tracing wraps and unwraps per
run, so it costs nothing when off; what is traced executes for real,
writes included, exactly like a run.
Guarantees:
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
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from dataclasses import dataclass

from ._atom_wire import _atom_from_wire
from ._space_execution import _controlled_run
from ._space_objects import _limits
from .atoms import Atom

__all__ = ["TraceEvent", "trace"]


@dataclass(frozen=True)
class TraceEvent:
    """One step: depth is the nesting level, kind is call or exit, term
    is what reduced, answer carries the exit's result and stays None on
    a call.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    depth: int
    kind: str
    term: Atom
    answer: Atom | None

    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.kind == "exit":
            return f"{indent}{self.term} = {self.answer}"
        return f"{indent}-> {self.term}"


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


class Trace(list):
    """The events, and whether the bound stopped the recording early.

    A list, because that is what a trace IS and every consumer wants to
    iterate it, index it and take its length. `truncated` is the one thing a
    plain list cannot say, and it has to be said: the bound is a COUNT and the
    memory an event costs is its term's size, so the honest answer to "trace
    this if it is cheap" is a prefix that admits to being one.
    """

    __slots__ = ("truncated",)

    def __init__(self, events=(), *, truncated: bool = False) -> None:
        super().__init__(events)
        self.truncated = truncated

    def __repr__(self) -> str:
        cut = ", truncated" if self.truncated else ""
        return f"Trace({len(self)} events{cut})"


def trace(space, source: Atom | str,
          max_events: int | None = None,
          *,
          timeout: float | None = None,
          inferences: int | None = None) -> Trace:
    """Run a term, or source, in this space under the engine's reduction trace.

    max_events bounds the RECORDING. Past it the recording STOPS and the
    result's `truncated` is True, so what was already recorded is answered
    rather than discarded: through 2026-09-03 the bound raised, which threw
    away every event and charged the full memory of the bound for no answer.

    timeout and inferences bound the RUN, the same pair every evaluating door
    takes and the same scoped `m.limits()` default behind them. The two bounds
    are independent because they stop different things: a program can retire
    millions of inferences inside a handful of recorded events, and through
    0.7.1 this door passed no limits at all, so `with m.limits(inferences=100)`
    let a traced program run 209,322 of them to completion
    [measured 2026-09-04, `!(loop 2000)` at inferences=100: run stopped at
    1,685 with InferenceLimitError, trace finished].
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
    truncated, records = _controlled_run(
        space.runtime,
        "metta_py_trace",
        [_as_source(source), space.name, int(max_events)],
        _limits(timeout, inferences),
    )
    # Events cross as terms on the ordinary wire. Read back from their own
    # text, a symbol whose spelling reads as something else arrived as
    # something else: (holds $notvar) traced as a variable while run
    # answered the symbol, and a tab inside a symbol split the record.
    events = []
    for record in records or []:
        depth, kind, term, *answer = record
        events.append(
            TraceEvent(
                int(depth),
                str(kind),
                _atom_from_wire(term),
                _atom_from_wire(answer[0]) if answer else None,
            )
        )
    return Trace(events, truncated=str(truncated) == "true")
