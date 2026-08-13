"""Purpose: the reduction trace as Python objects. m.trace(source) runs
source with every compiled MeTTa function wrapped engine-side, and
answers TraceEvent records: a call carries the term entering reduction
at its nesting depth, the matching exit carries the answer, and a call
with no exit is a reduction that failed. Tracing wraps and unwraps per
run, so it costs nothing when off; the source executes for real, writes
included, exactly like a run.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass

from .atoms import Atom, parse

__all__ = ["TraceEvent", "trace"]


@dataclass(frozen=True)
class TraceEvent:
    """One step: depth is the nesting level, kind is call or exit, term
    is what reduced, answer carries the exit's result and stays None on
    a call."""

    depth: int
    kind: str
    term: Atom
    answer: Atom | None

    def __str__(self) -> str:
        indent = "  " * self.depth
        if self.kind == "exit":
            return f"{indent}{self.term} = {self.answer}"
        return f"{indent}-> {self.term}"


def trace(space, source: str, max_events: int = 1_000_000) -> list[TraceEvent]:
    """Run source in this space under the engine's reduction trace.

    max_events bounds the recording: past it the trace raises instead
    of accumulating without limit, the same shape as the timeout and
    inference bounds elsewhere."""
    if max_events <= 0:
        raise ValueError(
            f"max_events must be positive, got {max_events!r}"
        )
    row = space.runtime.once(
        "metta_trace_source(Src, Space, Max, Events)",
        Src=source,
        Space=space.space_name,
        Max=int(max_events),
    )
    events = []
    for line in row.get("Events") or []:
        depth, kind, term_text, answer_text = str(line).split("\t")
        events.append(TraceEvent(
            int(depth),
            kind,
            parse(term_text),
            parse(answer_text) if answer_text else None,
        ))
    return events
