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

__all__ = ["Subscription", "Event", "subscribe", "bridge"]


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
    _fact: Atom | None = None  # the reflection atom in &petta, if any

    def drain(self) -> list[Event]:
        """Every queued event, oldest first; the queue empties."""
        events, self._queue = self._queue, []
        return events

    def cancel(self) -> None:
        if self._active:
            self._active = False
            _SUBSCRIPTIONS.remove(self)
            _sync_engine()
            if self._fact is not None and _RUNTIME is not None:
                from .ops import _reflect_remove

                _reflect_remove(_RUNTIME, self._fact)

    def _deliver(self, event: Event) -> None:
        if self.callback is None:
            self._queue.append(event)
        else:
            self.callback(event)


_SUBSCRIPTIONS: list[Subscription] = []
_RUNTIME = None


def _sync_engine() -> None:
    """Tell the engine which spaces have watchers: writes anywhere else
    never cross the boundary. The set, not a flag, is the whole point."""
    if _RUNTIME is not None:
        _RUNTIME.must(
            "petta_py_subscriptions(Spaces)",
            Spaces=sorted({s.space for s in _SUBSCRIPTIONS}),
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
    # The standing query reflects into the library's own space, removed on
    # cancel, so MeTTa programs see what Python is watching. The fact goes
    # in before the subscription activates: a watcher of &petta sees other
    # subscriptions arrive, never its own birth.
    from .atoms import Expr, Sym
    from .ops import _reflect_add

    subscription._fact = Expr(
        [Sym("subscription"), Sym(space), pattern, Sym(on)]
    )
    _reflect_add(runtime, subscription._fact)
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


# ------------------------------------------------------------ bridge rules


def _instantiate(template: Atom, bindings: Mapping[str, Atom]) -> Atom:
    from .atoms import Expr, Var

    if isinstance(template, Var):
        return bindings.get(template.name, template)
    if isinstance(template, Expr):
        return Expr([_instantiate(c, bindings) for c in template.children])
    return template


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
    from .space import _to_atom

    shape = _to_atom(pattern)
    built = shape if template is None else _to_atom(template)

    def deliver(event: Event) -> None:
        instantiated = _instantiate(built, event.bindings)
        if event.action == "add":
            target.add(instantiated)
        else:
            target.remove(instantiated)

    return source.subscribe(shape, deliver, on=on)
