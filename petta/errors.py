"""Purpose: the error types the petta library raises, and the Decline signal a
Python-backed operation uses to answer nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

__all__ = ["PettaError", "MettaSyntaxError", "EngineError", "Decline", "DECLINE"]


class PettaError(Exception):
    """Base class for everything this library raises on purpose."""


class MettaSyntaxError(PettaError):
    """The reader refused the source. Carries the engine's own message."""


class EngineError(PettaError):
    """A Prolog-side exception crossed the boundary.

    The original janus exception rides along as __cause__, so nothing is
    hidden; the message here is the engine's, trimmed of janus framing.
    """


class Decline(Exception):
    """Raised inside an operation to answer nothing at all.

    A deterministic operation that raises Decline makes the call fail rather
    than error, which is how a semi-deterministic MeTTa function says no. A
    generator operation needs no signal: yielding nothing already is one.
    """


#: Sentinel with the same meaning as raising Decline, for expression-shaped code.
DECLINE = Decline
