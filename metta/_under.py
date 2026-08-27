"""Purpose: carry the task-local algebra selected by ``with metta.under(...)``.

Guarantees:
  - an omitted per-call carrier reads the innermost scope, an explicit value
    wins, and exit restores the previous carrier even after an exception
    [tested: test_scoped_under_is_task_local_and_explicit_under_wins;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Final, Self

_UNSET: Final = object()
_SCOPED_UNDER: ContextVar[Any | None] = ContextVar(
    "metta_scoped_under", default=None
)


class ScopedUnder:
    """A dynamic algebra scope with ContextVar task and thread semantics."""

    __slots__ = ("_carrier", "_token")

    def __init__(self, carrier: Any) -> None:
        if carrier is None:
            msg = "under() needs an algebra carrier, not None"
            raise TypeError(msg)
        self._carrier = carrier
        self._token: Any = None

    def __enter__(self) -> Self:
        self._token = _SCOPED_UNDER.set(self._carrier)
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        _SCOPED_UNDER.reset(self._token)


def selected(explicit: Any = _UNSET) -> Any | None:
    """Resolve one call's explicit carrier before its surrounding scope."""
    if explicit is _UNSET:
        return _SCOPED_UNDER.get()
    if explicit is None:
        msg = "under= needs an algebra carrier, not None"
        raise TypeError(msg)
    return explicit


__all__ = ["ScopedUnder"]
