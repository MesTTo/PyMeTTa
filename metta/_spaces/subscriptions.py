"""Purpose: expose standing queries and iterators of space changes.

Owns resources: _WatchIterator.close cancels its subscription, and its
finalizer cancels an abandoned iterator
[source: extensions/python/metta/_spaces/subscriptions.py:59; commit=WORKTREE].
"""

from __future__ import annotations

import contextlib
import weakref
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Self

import metta._spaces.cursor as _spaces_cursor_module
import metta.doors as _doors
from metta._atoms.factories import _to_atom
from metta._errors.errors import Timeout
from metta._lazy import lazy
from metta.vocabularies import SubscriptionEdge


def _cancel_abandoned_subscription(subscription: Any) -> None:
    """The finalize backstop: best-effort, late-shutdown-safe."""
    with contextlib.suppress(Exception):
        subscription.cancel()

class _WatchIterator:
    """Own one eager subscription and cancel it whenever the iterator closes.

    close() is the contract; the weakref.finalize backstop only covers an
    ABANDONED iterator, so a dropped handle cannot keep a live subscription
    delivering into nothing [tested: test_an_abandoned_watch_cancels_itself].
    """

    __slots__ = ("__weakref__", "_deadline", "_events", "_finalizer", "_subscription")

    def __init__(self, subscription: Any, deadline: float | None = None) -> None:
        self._subscription = subscription
        self._deadline = deadline
        self._events: Iterator[Any] = subscription.events(deadline)
        self._finalizer = weakref.finalize(
            self, _cancel_abandoned_subscription, subscription
        )

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Any:
        try:
            return next(self._events)
        except StopIteration:
            self.close()
            if self._deadline is not None:
                msg = f"no matching change arrived within {self._deadline} seconds"
                raise Timeout(msg) from None
            raise

    def close(self) -> None:
        """Close the event generator and cancel the eager subscription once."""
        self._finalizer.detach()
        subscription = self._subscription
        if subscription is None:
            return
        self._subscription = None
        close = getattr(self._events, "close", None)
        try:
            if close is not None:
                close()
        finally:
            subscription.cancel()

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_take_peek_and_watch_retire_the_thread_linda_fn_strings', 'extensions/python/tests/ch11_python_as_a_notation/test_r5_unbuilt_doors.py::test_watch_close_before_first_event_cancels_its_eager_subscription', 'extensions/python/tests/ch16_events_and_standing_queries/test_events.py::test_an_abandoned_watch_cancels_itself'),
)
def watch(
    space: _root.Space,
    pattern: Any,
    *,
    on: SubscriptionEdge = SubscriptionEdge.add,
    where: Any | None = None,
    deadline: float | None = None,
    queue_max: int | None = None,
):
    """Yield matching changes, raising Timeout after each quiet deadline.

    `queue_max` bounds the subscription underneath, the same bound
    subscribe() takes; a watch could not name it before, though the
    subscription it builds always had one.
    """
    _spaces_cursor_module.require_deadline(deadline)
    return _WatchIterator(
        space.subscribe(pattern, on=on, where=where, queue_max=queue_max),
        deadline,
    )

@_doors.door(
    kind=_doors.Kind.scope,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_subscribe_is_the_function_watcher', 'extensions/python/tests/ch16_events_and_standing_queries/test_dispatch_index.py::test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order', 'extensions/python/tests/ch16_events_and_standing_queries/test_events.py::test_subscribe_bridge_and_reaction_are_expressible_over_the_public_event_stream'),
    async_signature=_doors.Signature('self, pattern: Any, *, on: str = "add", where: Any | None = None, queue_max: int = SUBSCRIPTION_QUEUE_MAX', returns=None),
    async_reason='the synchronous callback runs during delivery on the engine worker, while async consumers resume on their event loop. A caller callback cannot run on both threads; the async event stream is the delivery across that boundary and therefore has no callback parameter',
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:subscribe]'),),
)
def subscribe(
    space: _root.Space,
    pattern: Any,
    callback: Callable | None = None,
    *,
    on: SubscriptionEdge = SubscriptionEdge.add,
    where: Any | None = None,
    queue_max: int | None = None,
):
    """A standing query on this space: every added (or removed, or
    both) atom unifying with the pattern becomes an Event.

        seen = []
        sub = m.subscribe(S.order(V.id), lambda e: seen.append(e))
        m.add(S.order(1))          # seen[0].bindings["id"] == 1
        sub.cancel()

    With a callback, delivery is synchronous. An unscoped write delivers
    before it returns; a transaction delivers its ordered segment only
    after the complete commit, while rollback and speculation deliver
    nothing. The callback may write back; the engine re-enters cleanly,
    and an infinite add-triggers-add loop is the author's own.
    Without one, events queue on the subscription and drain() empties
    them: the mailbox reading. That queue is bounded by `queue_max`,
    and a write arriving at a full queue raises SubscriberError rather
    than discarding the oldest event: nobody draining is a bug in the
    consumer, and a silently shortened history is how it stays hidden.
    A removal event fires only when something was removed, and carries
    the pattern that was asked for rather than the occurrence that
    left. The two are the same atom for a ground removal and differ
    for a pattern one: removal is multiset subtraction, so
    `remove(S.alert(V.q))` takes one of the alerts and the event
    cannot say which. Re-read the space when you need to know;
    `m.live(pattern)` is the worked instance, and it is the rung above
    this one: a view is this subscription maintaining what a match would
    have answered.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    subscriptions = lazy('metta.subscribe')
    guard = None if where is None else _spaces_cursor_module.guard_atom(where)
    if where is not None and guard is None:
        msg = f"where= is a term the engine evaluates per event, got {where!r}"
        raise TypeError(msg)
    return subscriptions.subscribe(
        space._rt,
        space._space,
        _to_atom(pattern),
        callback,
        on,
        # None is the standing `(limit subscription-queue ...)` bound,
        # resolved where the subscription is made rather than here.
        queue_max=queue_max,
        # The guard becomes ONE admission test over the event, built by
        # the module that owns the instantiation and given this space's
        # own evaluation method, so a guard means on an event exactly what
        # it means on a match.
        admits=(
            None
            if guard is None
            else subscriptions.guard_admits(guard, space.eval)
        ),
    )

def _event_stream(space: _root.Space) -> Any:
    """This engine's stream of `(action, space, atom)` changes.

        seen = m.events().fold(
            lambda held, event: [*held, event.atom],
            space=m.name, pattern=S.order(V.id), state=[],
        )
        m.add(S.order(1))
        seen.take()          # [(order 1)], and the fold starts again

    The stream is the primitive and a FOLD over it is how anything
    consumes it: a step `(state, event) -> state` run immediately for an
    unscoped write or after the whole transaction commits. subscribe() is
    the fold whose step delivers, bridge() the fold whose step writes, and
    a declared `(on ...)` reaction the fold whose step evaluates, so a
    consumer you write and one this library ships are the same kind of
    thing.
    """
    return lazy('metta.events').stream(space._rt)

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
