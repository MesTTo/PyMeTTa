"""Purpose: carry the task-local algebra selected by ``with metta.under(...)``.

Guarantees:
  - algebra and demand cross internal evaluation without changing answer shape
    [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context.py -n 0; commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - an omitted per-call carrier reads the innermost scope, an explicit value
    wins, and exit restores the previous carrier even after an exception
    [tested: test_scoped_under_is_task_local_and_explicit_under_wins;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Final, Self

_UNSET: Final[object] = object()
_SCOPED_UNDER: ContextVar[Any | None] = ContextVar(
    "metta_scoped_under", default=None
)


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """The selected algebra and the demand carried by one evaluation."""

    algebra: str
    limit: int | None = None
    order: str | None = None

    def to_wire(self) -> list[Any]:
        """Encode the engine's evaluation_context term fields."""
        return [self.algebra, self.limit or 0, self.order or "none"]


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
