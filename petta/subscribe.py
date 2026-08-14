"""Purpose: standing queries. A subscription watches one space for atoms
unifying with a pattern and reacts to every add or removal: with a callback,
synchronously, inside the write that caused it; without one, by queuing
events for drain(). This is the actors-and-pub-sub reading of a space: the
mailbox is the space, the subscription is the standing query that maintains
itself, and the engine's own write hooks deliver.
Guarantees:
  - registry snapshots and queued event mutation are locked for
    free-threaded Python [tested test_subscription_queue_is_thread_safe,
    test_subscription_cancel_is_thread_safe]
Guarded by:
  - _SubscriptionRegistry._lock protects subscription state, the active
    runtime, and engine subscription snapshots [tested
    test_subscription_cancel_is_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from .atoms import Atom, Expr, Sym, Var, _to_atom, atom_from_wire, map_atoms, unify
from .foreign import require_capability
from .ops import _reflect_add, _reflect_remove

__all__ = ["Event", "Subscription", "bridge", "subscribe"]


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
    _fact: Expr | None = None  # the reflection atom in &petta, if any

    def drain(self) -> list[Event]:
        """Every queued event, oldest first; the queue empties."""
        return _REGISTRY.drain(self)

    def cancel(self) -> None:
        # The registry mutation is locked: two threads cancelling the
        # same subscription both used to pass the _active guard, and the
        # second list removal raised. Delivery never runs under the lock.
        runtime = _REGISTRY.cancel(self)
        if self._fact is not None and runtime is not None:
            _reflect_remove(runtime, self._fact)

    def _deliver(self, event: Event) -> None:
        if self.callback is None:
            _REGISTRY.queue(self, event)
        else:
            self.callback(event)


class _SubscriptionRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscriptions: list[Subscription] = []
        self.runtime = None

    def add(self, runtime, subscription: Subscription) -> None:
        with self._lock:
            self.runtime = runtime
            self._subscriptions.append(subscription)
            self._sync_locked()

    def cancel(self, subscription: Subscription):
        with self._lock:
            if not subscription._active:
                return None
            subscription._active = False
            self._subscriptions.remove(subscription)
            self._sync_locked()
            return self.runtime

    def drain(self, subscription: Subscription) -> list[Event]:
        with self._lock:
            events, subscription._queue = subscription._queue, []
            return events

    def queue(self, subscription: Subscription, event: Event) -> None:
        with self._lock:
            subscription._queue.append(event)

    def for_space(self, space: str) -> tuple[Subscription, ...]:
        with self._lock:
            return tuple(
                subscription
                for subscription in self._subscriptions
                if subscription._active and subscription.space == space
            )

    def _sync_locked(self) -> None:
        if self.runtime is None:
            return
        spaces = sorted({subscription.space for subscription in self._subscriptions})
        self.runtime.must("petta_py_subscriptions(Spaces)", Spaces=spaces)


_REGISTRY = _SubscriptionRegistry()


def _subscriptions_for(space: str) -> tuple[Subscription, ...]:
    return _REGISTRY.for_space(space)


def subscribe(
    runtime,
    space: str,
    pattern: Atom,
    callback: Callable[[Event], None] | None = None,
    on: str = "add",
) -> Subscription:
    if on not in ("add", "remove", "both"):
        raise ValueError(f"on must be add, remove or both, not {on!r}")
    require_capability(space, "subscribe", "subscribe", pattern=pattern, on=on)
    subscription = Subscription(space, pattern, callback, on)
    # The standing query reflects into the library's own space, removed on
    # cancel, so MeTTa programs see what Python is watching. The fact goes
    # in before the subscription activates: a watcher of &petta sees other
    # subscriptions arrive, never its own birth.
    subscription._fact = Expr([Sym("subscription"), Sym(space), pattern, Sym(on)])
    _reflect_add(runtime, subscription._fact)
    _REGISTRY.add(runtime, subscription)
    return subscription


# ------------------------------------------------- called from the shim


def _dispatch(action: str, space: str, wire: list) -> bool:
    atom = atom_from_wire(wire)
    for subscription in _subscriptions_for(space):
        if subscription.on not in ("both", action):
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


# ------------------------------------------------------------ bridge rules


def _instantiate(template: Atom, bindings: Mapping[str, Atom]) -> Atom:
    return map_atoms(
        template,
        lambda atom: bindings.get(atom.name, atom) if isinstance(atom, Var) else atom,
    )


def bridge(source, pattern, target, template=None, on: str = "add") -> Subscription:
    """A bridge rule between spaces, the multi-context-systems reading:
    when an atom unifying with pattern arrives in source, the template's
    instantiation under the match's bindings lands in target, and with
    on="both" a removal in source removes the instantiation from target,
    the mirrored rule.

        rule = petta.bridge(src, S.alarm(V.zone), dst, S.notify(V.zone))
        src.add(S.alarm(S.kitchen))        # dst now holds (notify kitchen)
        rule.cancel()

    template defaults to the pattern itself. The rule is a standing
    query, delivered inside the write that triggered it; target needs
    only add and remove, so a remote.attach()ed space bridges across
    engines identically."""
    shape = _to_atom(pattern)
    built = shape if template is None else _to_atom(template)

    def deliver(event: Event) -> None:
        instantiated = _instantiate(built, event.bindings)
        if event.action == "add":
            target.add(instantiated)
        else:
            target.remove(instantiated)

    return source.subscribe(shape, deliver, on=on)
