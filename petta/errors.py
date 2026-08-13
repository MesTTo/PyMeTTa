"""Purpose: the error types the petta library raises, and the Decline signal a
Python-backed operation uses to answer nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

__all__ = [
    "PettaError",
    "MettaSyntaxError",
    "EngineError",
    "ResourceLimitError",
    "TimeLimitError",
    "InferenceLimitError",
    "CompileError",
    "Decline",
    "DECLINE",
]


class PettaError(Exception):
    """Base class for everything this library raises on purpose."""


class MettaSyntaxError(PettaError):
    """The reader refused the source. Carries the engine's own message."""


class EngineError(PettaError):
    """A Prolog-side exception crossed the boundary.

    The original janus exception rides along as __cause__, so nothing is
    hidden; the message here is the engine's, trimmed of janus framing.
    """


class ResourceLimitError(EngineError):
    """A per-call resource guard stopped the evaluation.

    The guard is the caller's own timeout= or inferences= bound. Whatever
    the goal completed before the stop, writes included, stands; that is
    what stopping a computation mid-way means everywhere.
    """


class TimeLimitError(ResourceLimitError):
    """timeout= seconds elapsed before the call finished."""


class InferenceLimitError(ResourceLimitError):
    """inferences= engine steps were spent before the call finished."""


class CompileError(PettaError):
    """A Python construct the define compiler refuses, with the reason.

    Refusals are the contract: every one names the construct, the line, and
    what to write instead, so the message teaches the subset rather than
    hiding it. Never a silent fallback.
    """

    def __init__(self, message: str, *, construct: str | None = None, line: int | None = None):
        where = f" (line {line})" if line is not None else ""
        super().__init__(f"{message}{where}")
        self.construct = construct
        self.line = line


class Decline(Exception):
    """Raised inside an operation to answer nothing at all.

    A deterministic operation that raises Decline makes the call fail rather
    than error, which is how a semi-deterministic MeTTa function says no. A
    generator operation needs no signal: yielding nothing already is one.
    """


#: Sentinel with the same meaning as raising Decline, for expression-shaped code.
DECLINE = Decline
