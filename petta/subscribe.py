"""Purpose: standing queries. A subscription watches one space for atoms
unifying with a pattern and reacts to every add or removal: with a callback,
synchronously, inside the write that caused it; without one, by queuing
events for drain(). This is the actors-and-pub-sub reading of a space: the
mailbox is the space, the subscription is the standing query that maintains
itself, and the engine's own write hooks deliver.

Every write consults the subscriptions on its space, so the dispatch is on
the write path and its cost is the write's. It goes through the
discrimination tree in petta.structures rather than one unify per
subscription [measured 2026-08-19, 1000 standing queries on one space and
200 writes, controlled instructions:u min of 3: 4012009981 scanning against
48243634 indexed, 83.2x, both delivering 200 of 200].
Guarantees:
  - registry snapshots and queued event mutation are locked for
    free-threaded Python [tested test_subscription_queue_is_thread_safe,
    test_subscription_cancel_is_thread_safe]
  - subscription publication and cancellation update registry state, engine
    write guards, and reflection facts together or restore the prior state
    [tested test_subscription_lifecycle_rolls_back_failed_boundaries]
  - cancel waits for callbacks already in flight and stale dispatch snapshots
    cannot deliver after cancellation [tested
    test_subscription_cancel_waits_for_inflight_delivery,
    test_stale_subscription_snapshot_cannot_deliver_after_cancel]
  - identical subscriptions share one reflection descriptor until the last
    subscription cancels [tested
    test_identical_subscriptions_share_one_reflection_fact]
  - a watcher that raises reaches the writer as SubscriberError, naming the
    subscription and saying the write stands, where a refused write does
    not [measured 2026-08-19: both arrived as EngineError with the same
    "Python '<Type>': <text>" message template, so a caller could only tell
    them apart by reading the sentence] [tested
    test_a_watcher_failure_is_distinguishable_from_a_failed_write]
  - dispatch answers the same subscriptions in the same order the linear
    scan did, cancels and re-subscriptions included [measured 2026-08-19:
    routed through the tree before its entry ids were made monotonic, every
    subscriber still fired and two swapped places] [tested
    test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order]
Guarded by:
  - _SubscriptionRegistry._lock protects subscription state, the active
    runtime, delivery counts, and engine subscription snapshots [tested
    test_subscription_cancel_is_thread_safe]
  - _TRANSACTION_LOCK serializes cross-boundary subscription lifecycle
    changes [tested test_subscription_lifecycle_rolls_back_failed_boundaries]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final, Self

from .atoms import (
    Atom,
    Expr,
    Sym,
    Var,
    _to_atom,
    atom_from_wire,
    is_ground,
    map_atoms,
    unify,
)
from .errors import EngineError, PettaError, SubscriberError
from .foreign import require_capability
from .ops import REFLECTION_SPACE, _reflect_add, _reflect_remove
from .structures import MatchIndex
from .vocabularies import SUBSCRIPTION_EDGE

__all__ = ["Event", "Subscription", "bridge", "subscribe"]


@dataclass(frozen=True)
class Event:
    """One delivery: what happened, where, to which atom, with which
    bindings the pattern took.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    action: str  # "add" | "remove"
    space: str
    atom: Atom
    bindings: Mapping[str, Atom]


#: How many undrained events one subscription holds before it refuses more.
#: A queue nobody drains grew for the life of the process; this is what
#: replaces that. queue.Queue is the precedent for the POLICY: put_nowait on
#: a full queue raises rather than dropping, where collections.deque(maxlen=)
#: discards the oldest without telling anyone.
SUBSCRIPTION_QUEUE_MAX: Final[int] = 10_000


@dataclass(eq=False)
class Subscription:
    """One standing query; cancel() ends it. With no callback, events
    queue and drain() empties the queue.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    space: str
    pattern: Atom
    callback: Callable[[Event], None] | None
    on: str  # "add" | "remove" | "both"
    queue_max: int = SUBSCRIPTION_QUEUE_MAX
    _queue: list[Event] = field(default_factory=list)
    _active: bool = True
    _fact: Expr | None = None  # the reflection atom in &petta, if any

    def drain(self) -> list[Event]:
        """Every queued event, oldest first; the queue empties."""
        return _REGISTRY.drain(self)

    def events(self, timeout: float | None = None):
        """Incoming events as a blocking stream: the no-callback queue
        mode consumed without polling, so a consumer thread writes
        `for event in sub.events(): ...` and sleeps on a condition
        variable between arrivals. The stream ends when the subscription
        cancels, queued leftovers delivered first, or when `timeout`
        seconds pass with nothing arriving. A callback subscription
        delivers through its callback and has no queue, so it refuses.
        Bare `iter(sub)` is deliberately absent: iteration that blocks
        should say so by name.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self.callback is not None:
            msg = (
                "events() consumes the no-callback queue; this subscription "
                "delivers through its callback"
            )
            raise PettaError(
                msg
            )
        while True:
            arrived = _REGISTRY.take(self, timeout)
            if not arrived:
                return
            yield from arrived

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.cancel()

    def cancel(self) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        with _TRANSACTION_LOCK:
            cancellation = _REGISTRY.cancel(self)
            if cancellation is not None and self._fact is not None:
                try:
                    if not _REGISTRY.has_fact(self._fact):
                        _ensure_reflection_absent(cancellation.runtime, self._fact)
                except BaseException as removal_error:
                    rollback_errors: list[BaseException] = []
                    try:
                        _ensure_reflection_present(cancellation.runtime, self._fact)
                    except (PettaError, RuntimeError, BaseExceptionGroup) as rollback_error:
                        rollback_errors.append(rollback_error)
                    try:
                        _REGISTRY.restore(cancellation, self)
                    except (PettaError, RuntimeError, BaseExceptionGroup) as rollback_error:
                        rollback_errors.append(rollback_error)
                    if rollback_errors:
                        msg = "subscription cancellation and rollback both failed"
                        raise BaseExceptionGroup(
                            msg,
                            [removal_error, *rollback_errors],
                        ) from None
                    raise
        _REGISTRY.wait_for_deliveries(self)

    def _deliver(self, event: Event) -> None:
        if not _REGISTRY.begin_delivery(self):
            return
        try:
            if self.callback is None:
                _REGISTRY.queue(self, event)
            else:
                self.callback(event)
        finally:
            _REGISTRY.end_delivery(self)


@dataclass(frozen=True)
class _Cancellation:
    runtime: Any
    order: tuple[Subscription, ...]
    index: int


class _SubscriptionRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._delivery_changed = threading.Condition(self._lock)
        self._arrived = threading.Condition(self._lock)
        self._subscriptions: list[Subscription] = []
        self._deliveries: dict[Subscription, dict[int, int]] = {}
        # One discrimination tree per space, so N stays per-space exactly as
        # the scan's own space filter made it.
        self._indexes: dict[str, MatchIndex] = {}
        self.runtime = None

    def add(self, runtime, subscription: Subscription) -> None:
        with self._lock:
            if self.runtime is not None and self.runtime is not runtime:
                msg = "subscriptions cannot span distinct engine runtimes in one process"
                raise RuntimeError(
                    msg
                )
            if any(current is subscription for current in self._subscriptions):
                msg = "the subscription is already registered"
                raise RuntimeError(msg)
            candidate = [*self._subscriptions, subscription]
            self._publish_locked(runtime, candidate)
            self.runtime = runtime
            self._subscriptions = candidate
            self._indexes.setdefault(subscription.space, MatchIndex()).add(
                subscription.pattern, subscription
            )

    def cancel(self, subscription: Subscription) -> _Cancellation | None:
        with self._lock:
            if not subscription._active:
                return None
            index = next(
                (
                    position
                    for position, current in enumerate(self._subscriptions)
                    if current is subscription
                ),
                None,
            )
            if index is None:
                msg = "an active subscription is missing from the registry"
                raise RuntimeError(msg)
            if self.runtime is None:
                msg = "the subscription registry has no engine runtime"
                raise RuntimeError(msg)
            order = tuple(self._subscriptions)
            candidate = self._subscriptions.copy()
            candidate.pop(index)
            self._publish_locked(self.runtime, candidate)
            self._subscriptions = candidate
            subscription._active = False
            tree = self._indexes.get(subscription.space)
            if tree is not None:
                tree.remove(subscription.pattern, subscription)
            self._arrived.notify_all()  # events() streams end at cancel
            return _Cancellation(self.runtime, order, index)

    def restore(self, cancellation: _Cancellation, subscription: Subscription) -> None:
        with self._lock:
            if subscription._active or any(
                current is subscription for current in self._subscriptions
            ):
                msg = "cannot restore an active subscription"
                raise RuntimeError(msg)
            if self.runtime is not cancellation.runtime:
                msg = "cannot restore a subscription on another runtime"
                raise RuntimeError(msg)
            candidate = self._subscriptions.copy()
            candidate.insert(self._restoration_index(cancellation), subscription)
            self._publish_locked(cancellation.runtime, candidate)
            self._subscriptions = candidate
            subscription._active = True
            # Restoration puts a subscription back where it WAS, so appending
            # to the tree would file it last. Rebuilding the one space's tree
            # from the restored order is the only spelling that keeps
            # delivery order equal to registration order, and this is the
            # rollback path, where O(N) is not the concern.
            self._rebuild_locked(subscription.space)

    def drain(self, subscription: Subscription) -> list[Event]:
        with self._lock:
            events, subscription._queue = subscription._queue, []
            return events

    def queue(self, subscription: Subscription, event: Event) -> None:
        with self._lock:
            if len(subscription._queue) >= subscription.queue_max:
                msg = (
                    f"the queue holds its limit of {subscription.queue_max} "
                    f"undrained events and this one has nowhere to go. Call "
                    f"drain() or consume events(), give the subscription a "
                    f"callback so delivery never queues, or raise "
                    f"queue_max=. Dropping the oldest silently is the one "
                    f"thing it will not do."
                )
                raise PettaError(
                    msg,
                    atom=event.atom,
                    space=subscription.space,
                )
            subscription._queue.append(event)
            self._arrived.notify_all()

    def take(self, subscription: Subscription, timeout: float | None) -> list[Event]:
        """Queued events, blocking until something arrives, the
        subscription cancels, or the timeout elapses; empty means the
        stream is over. The condition is shared, so a wake for another
        subscription re-checks against the remaining deadline.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._lock:
            while subscription._active and not subscription._queue:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return []
                self._arrived.wait(remaining)
            events, subscription._queue = subscription._queue, []
            return events

    def begin_delivery(self, subscription: Subscription) -> bool:
        with self._lock:
            if not subscription._active:
                return False
            thread_id = threading.get_ident()
            counts = self._deliveries.setdefault(subscription, {})
            counts[thread_id] = counts.get(thread_id, 0) + 1
            return True

    def end_delivery(self, subscription: Subscription) -> None:
        with self._lock:
            thread_id = threading.get_ident()
            counts = self._deliveries.get(subscription)
            if counts is None or counts.get(thread_id, 0) == 0:
                msg = "subscription delivery accounting is unbalanced"
                raise RuntimeError(msg)
            if counts[thread_id] == 1:
                del counts[thread_id]
            else:
                counts[thread_id] -= 1
            if not counts:
                del self._deliveries[subscription]
            self._delivery_changed.notify_all()

    def wait_for_deliveries(self, subscription: Subscription) -> None:
        """Wait for other threads; a callback may cancel itself safely."""
        thread_id = threading.get_ident()
        with self._delivery_changed:
            self._delivery_changed.wait_for(
                lambda: (
                    not any(
                        owner != thread_id and count
                        for owner, count in self._deliveries.get(subscription, {}).items()
                    )
                )
            )

    def for_space(self, space: str) -> tuple[Subscription, ...]:
        with self._lock:
            return tuple(
                subscription
                for subscription in self._subscriptions
                if subscription._active and subscription.space == space
            )

    def candidates(self, space: str, atom: Atom) -> tuple[Subscription, ...]:
        """The subscriptions on this space whose pattern could match the
        atom, in registration order.

        A superset of the ones that WILL match is all this owes: the caller
        unifies anyway, because it needs the bindings. What it owes exactly
        is the order and the completeness.

        A probe carrying variables goes down the list instead. The tree
        reads probe tokens literally, so a variable in the probe would need
        every edge followed at once, and MatchIndex answers that by scanning
        its whole entry table and sorting it, which is more work than the
        list this registry already keeps in order. An atom with variables in
        it is a real thing to store, `(rule $x)` reads back as
        `(rule $_608)`, so this is a shape the write path meets rather than
        one it can refuse.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        with self._lock:
            if not is_ground(atom):
                return tuple(
                    subscription
                    for subscription in self._subscriptions
                    if subscription._active and subscription.space == space
                )
            tree = self._indexes.get(space)
            if tree is None:
                return ()
            return tuple(subscription for _pattern, subscription in tree.matches(atom))

    def _rebuild_locked(self, space: str) -> None:
        tree = MatchIndex()
        for subscription in self._subscriptions:
            if subscription._active and subscription.space == space:
                tree.add(subscription.pattern, subscription)
        self._indexes[space] = tree

    def has_fact(self, fact: Expr) -> bool:
        with self._lock:
            return any(
                subscription._active and subscription._fact == fact
                for subscription in self._subscriptions
            )

    def _publish_locked(self, runtime: Any, subscriptions: list[Subscription]) -> None:
        current_spaces = self._spaces(self._subscriptions)
        candidate_spaces = self._spaces(subscriptions)
        if current_spaces == candidate_spaces:
            return
        try:
            runtime.must("petta_py_subscriptions(Spaces)", Spaces=candidate_spaces)
        except BaseException as publication_error:
            try:
                runtime.must("petta_py_subscriptions(Spaces)", Spaces=current_spaces)
            except (PettaError, RuntimeError, BaseExceptionGroup) as rollback_error:
                msg = "subscription guard publication and rollback both failed"
                raise BaseExceptionGroup(
                    msg,
                    [publication_error, rollback_error],
                ) from None
            raise

    def _restoration_index(self, cancellation: _Cancellation) -> int:
        for successor in cancellation.order[cancellation.index + 1 :]:
            for index, current in enumerate(self._subscriptions):
                if current is successor:
                    return index
        for predecessor in reversed(cancellation.order[: cancellation.index]):
            for index, current in enumerate(self._subscriptions):
                if current is predecessor:
                    return index + 1
        return min(cancellation.index, len(self._subscriptions))

    @staticmethod
    def _spaces(subscriptions: list[Subscription]) -> list[str]:
        return sorted({subscription.space for subscription in subscriptions})


_REGISTRY = _SubscriptionRegistry()
_TRANSACTION_LOCK = threading.RLock()


def _reflection_contains(runtime: Any, fact: Expr) -> bool:
    return runtime.do("petta_py_contains", REFLECTION_SPACE, fact.to_wire())


def _ensure_reflection_present(runtime: Any, fact: Expr) -> None:
    if not _reflection_contains(runtime, fact):
        _reflect_add(runtime, fact)
    if not _reflection_contains(runtime, fact):
        msg = f"the engine did not retain reflection fact {fact}"
        raise EngineError(msg)


def _ensure_reflection_absent(runtime: Any, fact: Expr) -> None:
    if _reflection_contains(runtime, fact):
        _reflect_remove(runtime, fact)
    if _reflection_contains(runtime, fact):
        msg = f"the engine did not remove reflection fact {fact}"
        raise EngineError(msg)


def _subscriptions_for(space: str) -> tuple[Subscription, ...]:
    return _REGISTRY.for_space(space)


def subscribe(  # noqa: D103  -- the package reference and enclosing module document this exported entry point
    runtime,
    space: str,
    pattern: Atom,
    callback: Callable[[Event], None] | None = None,
    on: str = "add",
    *,
    queue_max: int = SUBSCRIPTION_QUEUE_MAX,
) -> Subscription:
    if on not in SUBSCRIPTION_EDGE:
        msg = f"on must be one of {', '.join(SUBSCRIPTION_EDGE)}, not {on!r}"
        raise ValueError(
            msg
        )
    if queue_max < 1:
        msg = f"queue_max must be at least 1, not {queue_max!r}"
        raise ValueError(msg)
    require_capability(space, "subscribe", "subscribe", pattern=pattern, on=on)
    subscription = Subscription(space, pattern, callback, on, queue_max)
    # The standing query reflects into the library's own space, removed on
    # cancel, so MeTTa programs see what Python is watching. The fact goes
    # in before the subscription activates: a watcher of &petta sees other
    # subscriptions arrive, never its own birth.
    subscription._fact = Expr([Sym("subscription"), Sym(space), pattern, Sym(on)])
    with _TRANSACTION_LOCK:
        try:
            _ensure_reflection_present(runtime, subscription._fact)
            _REGISTRY.add(runtime, subscription)
        except BaseException as publication_error:
            subscription._active = False
            rollback_errors: list[BaseException] = []
            try:
                if _REGISTRY.has_fact(subscription._fact):
                    _ensure_reflection_present(runtime, subscription._fact)
                else:
                    _ensure_reflection_absent(runtime, subscription._fact)
            except (PettaError, RuntimeError, BaseExceptionGroup) as rollback_error:
                rollback_errors.append(rollback_error)
            if rollback_errors:
                msg = "subscription publication and rollback both failed"
                raise BaseExceptionGroup(
                    msg,
                    [publication_error, *rollback_errors],
                ) from None
            raise
    return subscription


# ------------------------------------------------- called from the shim


def _dispatch(action: str, space: str, wire: list) -> bool:
    atom = atom_from_wire(wire)
    for subscription in _REGISTRY.candidates(space, atom):
        if subscription.on not in ("both", action):
            continue
        bindings = unify(subscription.pattern, atom)
        if bindings is None:
            continue
        try:
            subscription._deliver(Event(action, space, atom, bindings))
        # A control signal is BaseException and passes through untouched:
        # KeyboardInterrupt is not a watcher saying no.
        except Exception as failure:
            msg = (
                f"{space} applied the {action} of {atom} and then a watcher "
                f"failed. This is not a failed write: retrying it stores a "
                f"second copy, because a space is a multiset, and an "
                f"enclosing atomic run or a (transaction ...) scope is the "
                f"one thing that undoes it, as this error leaves the scope. "
                f"Delivering to the subscription on {subscription.pattern} "
                f"raised {type(failure).__name__}: {failure}"
            )
            raise SubscriberError(
                msg,
                subscription=subscription,
                action=action,
                atom=atom,
                space=space,
            ) from failure
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
    engines identically.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    shape = _to_atom(pattern)
    built = shape if template is None else _to_atom(template)

    def deliver(event: Event) -> None:
        instantiated = _instantiate(built, event.bindings)
        if event.action == "add":
            target.add(instantiated)
        else:
            target.remove(instantiated)

    return source.subscribe(shape, deliver, on=on)
