"""Purpose: the error types the petta library raises, and the Decline signal a
Python-backed operation uses to answer nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

__all__ = [
    "DECLINE",
    "CompileError",
    "Decline",
    "EngineError",
    "InferenceLimitError",
    "Interrupted",
    "MettaOperationError",
    "MettaSyntaxError",
    "PettaError",
    "ResourceLimitError",
    "SourceNotFound",
    "StrictError",
    "TimeLimitError",
    "TransportFailure",
    "is_transport_failure",
]


class PettaError(Exception):
    """Base class for everything this library raises on purpose."""


class MettaSyntaxError(PettaError):
    """The reader refused the source. Carries the engine's own message."""


class SourceNotFound(PettaError, FileNotFoundError):
    """A file this library was asked to load is not there.

    Both bases on purpose. A caller reaching for a source file writes
    `except FileNotFoundError`, and a caller wrapping a whole registration
    writes `except PettaError`; one exception answering to both is what
    stops the second reading from silently missing this case, which is what
    a plain FileNotFoundError did.
    """


class EngineError(PettaError):
    """A Prolog-side exception crossed the boundary.

    The original janus exception rides along as __cause__, so nothing is
    hidden; the message here is the engine's, trimmed of janus framing.
    """


class MettaOperationError(EngineError):
    """A builtin refused a value, naming the operation the source wrote.

    The engine keeps the ISO formal term and adds the written operation, so
    the parts arrive as data: `operation` is what to look for in the source,
    `kind` is the formal's functor, and `expected` and `culprit` carry the
    type and the offending value when the formal is a type error. Catching
    EngineError still catches this.
    """

    def __init__(
        self,
        message: str,
        *,
        operation: str,
        kind: str,
        expected: object | None = None,
        culprit: object | None = None,
    ):
        super().__init__(message)
        self.operation = operation
        self.kind = kind
        self.expected = expected
        self.culprit = culprit


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


class Interrupted(EngineError):
    """interrupt() stopped the evaluation mid-goal.

    The sqlite3 and DuckDB reading of interrupt: whatever the goal
    completed before the stop, writes included, stands.
    """


class StrictError(PettaError):
    """An opt-in strict run or eval refused an answer nothing reduced.

    Strict means every directive must reduce. `term` is the answer the
    engine handed back unevaluated, and `directive` is its 1-based position
    in the source. An empty answer is NOT a violation: a pruned branch is
    what (empty) and a match with no candidates produce, and refusing it
    would refuse ordinary MeTTa.
    """

    def __init__(self, message: str, *, term: object = None, directive: int | None = None):
        where = f"directive {directive}: " if directive is not None else ""
        super().__init__(f"{where}{message}")
        self.term = term
        self.directive = directive


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


class TransportFailure(PettaError):
    """The backend is ABSENT rather than wrong: a connection, a timeout, a
    closed stream. The seam's error trichotomy treats these differently
    from application errors: a declared keep or empty mode never applies,
    transport always aborts, because retrying or giving up is the caller's
    decision and an absent backend has said nothing about the data."""


def is_transport_failure(error: BaseException) -> bool:
    """Whether an error is the backend being ABSENT rather than wrong.

    The obvious test does not separate them: a socket timeout raises
    OSError, but websocket-client's own timeout does NOT subclass it, so
    "is the cause an OSError" misses exactly the shape a broken event
    stream takes under load. Hoisted from the DAS surface to the seam,
    because every remote backend needs the same trichotomy.
    """
    from ._optional import optional_module  # noqa: PLC0415  optional probe

    cause = error.__cause__ if isinstance(error, PettaError) else error
    if isinstance(error, TransportFailure):
        return True
    if isinstance(cause, (OSError, TimeoutError)):
        return True
    module = optional_module("websocket")
    if module is None:
        return False
    return isinstance(
        cause,
        (module.WebSocketTimeoutException, module.WebSocketConnectionClosedException),
    )


class Decline(Exception):
    """Raised inside an operation to answer nothing at all.

    A deterministic operation that raises Decline makes the call fail rather
    than error, which is how a semi-deterministic MeTTa function says no. A
    generator operation needs no signal: yielding nothing already is one.
    """


#: Sentinel with the same meaning as raising Decline, for expression-shaped code.
DECLINE = Decline
