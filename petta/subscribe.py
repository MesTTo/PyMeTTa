"""Purpose: standing queries. A subscription watches one space for atoms
unifying with a pattern and reacts to every add or removal: with a callback,
synchronously, inside the write that caused it; without one, by queuing
events for drain(). This is the actors-and-pub-sub reading of a space: the
mailbox is the space, the subscription is the standing query that maintains
itself, and the engine's own write hooks deliver.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .atoms import Atom, from_wire, unify

__all__ = ["Subscription", "Event", "subscribe"]


@dataclass(frozen=True)
class Event:
    """One delivery: what happened, where, to which atom, with which
    bindings the pattern took."""

    action: str  # "add" | "remove"
    space: str
    atom: Atom
    bindings: Mapping[str, Atom]


@dataclass
class Subscription:
    """One standing query; cancel() ends it. With no callback, events
    queue and drain() empties the queue."""

    space: str
    pattern: Atom
    callback: Callable[[Event], None] | None
    on: str  # "add" | "remove" | "both"
    _queue: list[Event] = field(default_factory=list)
    _active: bool = True

    def drain(self) -> list[Event]:
        """Every queued event, oldest first; the queue empties."""
        events, self._queue = self._queue, []
        return events

    def cancel(self) -> None:
        if self._active:
            self._active = False
            _SUBSCRIPTIONS.remove(self)
            _sync_engine()

    def _deliver(self, event: Event) -> None:
        if self.callback is None:
            self._queue.append(event)
        else:
            self.callback(event)


_SUBSCRIPTIONS: list[Subscription] = []
_RUNTIME = None


def _sync_engine() -> None:
    if _RUNTIME is not None:
        _RUNTIME.must(
            "petta_py_subscriptions(E)",
            E="true" if _SUBSCRIPTIONS else "false",
        )


def subscribe(
    runtime,
    space: str,
    pattern: Atom,
    callback: Callable[[Event], None] | None = None,
    on: str = "add",
) -> Subscription:
    global _RUNTIME
    if on not in ("add", "remove", "both"):
        raise ValueError(f"on must be add, remove or both, not {on!r}")
    _RUNTIME = runtime
    subscription = Subscription(space, pattern, callback, on)
    _SUBSCRIPTIONS.append(subscription)
    _sync_engine()
    return subscription


# ------------------------------------------------- called from the shim


def _dispatch(action: str, space: str, wire: list) -> bool:
    atom = from_wire(wire)
    for subscription in list(_SUBSCRIPTIONS):
        if not subscription._active or subscription.space != space:
            continue
        if subscription.on != "both" and subscription.on != action:
            continue
        bindings = unify(subscription.pattern, atom)
        if bindings is None:
            continue
        subscription._deliver(Event(action, space, atom, bindings))
    return True


def atom_added(space: str, wire: list) -> bool:
    return _dispatch("add", space, wire)


def atom_removed(space: str, wire: list) -> bool:
    return _dispatch("remove", space, wire)
