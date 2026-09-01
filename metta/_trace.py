"""Purpose: the reduction trace as Python objects. m.trace(term) runs
that term with every compiled MeTTa function wrapped engine-side, and
answers TraceEvent records: a call carries the term entering reduction
at its nesting depth, the matching exit carries the answer, and a call
with no exit is a reduction that failed. Tracing wraps and unwraps per
run, so it costs nothing when off; what is traced executes for real,
writes included, exactly like a run.
Guarantees:
  - a term and the source that spells it trace identically, so the one
    door that shows a reduction takes the argument every other door
    takes [tested test_trace_takes_the_term_every_other_door_takes]
  - traced source keeps run()'s real-write semantics while inheriting the
    same speculative execution fence [tested:
    test_every_public_execution_door_honours_speculative_policy;
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
    trace took only text, so the one door that shows you a reduction was
    the one door that made you write the program twice. The tracer runs
    SOURCE, so a term is written and prefixed with the `!` that makes it
    a runnable form; `str(Atom)` is the writer the whole surface prints
    through, which is why `.source()` on a definition reads back as MeTTa.
    A string is passed through untouched, `!` included or not, so every
    call written before this still means what it meant.
    """
    return what if isinstance(what, str) else f"!{what}"


def trace(space, source: Atom | str, max_events: int = 1_000_000) -> list[TraceEvent]:
    """Run a term, or source, in this space under the engine's reduction trace.

    max_events bounds the recording: past it the trace raises instead
    of accumulating without limit, the same shape as the timeout and
    inference bounds elsewhere.
    """
    if max_events <= 0:
        msg = f"max_events must be positive, got {max_events!r}"
        raise ValueError(
            msg
        )
    records = _controlled_run(
        space.runtime,
        "metta_py_trace",
        [_as_source(source), space.name, int(max_events)],
        None,
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
    return events
