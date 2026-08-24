"""Purpose: the two delivery models the library ships over the public event
stream. A subscription is the fold that DELIVERS, to a callback
synchronously inside the write or to a queue drain() empties; a bridge is
the fold that WRITES, landing a template's instantiation in another space.
Both are `metta.events.EventStream.fold` with a different step and nothing
else, which is what makes "a third party could have written these" a fact
rather than a claim.

This is the actors-and-pub-sub reading of a space: the mailbox is the
space, the subscription is the standing query that maintains itself, and
the engine's own write hooks deliver. Every write consults the folds on its
space, so the dispatch is on the write path and its cost is the write's;
metta.events owns that dispatch and its discrimination tree.
Guarantees:
  - subscription publication and cancellation update registry state, engine
    write guards, and reflection facts together or restore the prior state
    [tested test_subscription_lifecycle_rolls_back_failed_boundaries]
  - identical subscriptions share one reflection descriptor until the last
    subscription cancels [tested
    test_identical_subscriptions_share_one_reflection_fact]
  - a watcher that raises reaches the writer as SubscriberError, naming the
    subscription and saying the write stands, where a refused write does
    not [measured 2026-08-19: both arrived as EngineError with the same
    "Python '<Type>': <text>" message template, so a caller could only tell
    them apart by reading the sentence] [tested
    test_a_watcher_failure_is_distinguishable_from_a_failed_write]
  - a queue nobody drains refuses rather than dropping the oldest event
    [tested test_the_subscription_queue_is_bounded_and_load_takes_a_budget]
Guarded by:
  - metta.events' fold registry lock protects queue state and the engine
    subscription snapshot [tested test_subscription_cancel_is_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from typing import Any, Final, Self

from .atoms import Atom, Expression, Symbol, Variable, _map_atoms, _to_atom
from .errors import EngineError, PettaError
from .events import _REGISTRY, STATELESS, Event, Fold
from .foreign import require_capability
from .ops import _REFLECTION_SPACE, _reflect_add, _reflect_remove
from .vocabularies import SubscriptionEdge

__all__ = ["Event", "Subscription", "bridge", "subscribe"]


#: How many undrained events one subscription holds before it refuses more.
#: A queue nobody drains grew for the life of the process; this is what
#: replaces that. queue.Queue is the precedent for the POLICY: put_nowait on
#: a full queue raises rather than dropping, where collections.deque(maxlen=)
#: discards the oldest without telling anyone.
SUBSCRIPTION_QUEUE_MAX: Final[int] = 10_000


class Subscription(Fold):
    """One standing query; cancel() ends it.

    The delivering fold: its step calls the callback, or appends to the
    fold's own state, which is the queue drain() empties.
    """

    __slots__ = ("_fact", "callback", "queue_max")

    def __init__(
        self,
        space: str,
        pattern: Atom,
        callback: Callable[[Event], None] | None,
        on: str,
        queue_max: int = SUBSCRIPTION_QUEUE_MAX,
    ) -> None:
        """Build the standing query; subscribe() publishes it."""
        super().__init__(
            _REGISTRY, space, pattern, self._step_over,
            on=on,
            state=STATELESS if callback is not None else [],
        )
        self.callback = callback
        self.queue_max = queue_max
        self._fact: Expression | None = None  # the reflection atom in &petta, if any

    def _step_over(self, held: list[Event], event: Event) -> list[Event]:
        """Deliver, or queue. The two shipped delivery disciplines, as one
        step over the fold's state.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self.callback is not None:
            self.callback(event)
            return held
        if len(held) >= self.queue_max:
            msg = (
                f"the queue holds its limit of {self.queue_max} "
                f"undrained events and this one has nowhere to go. Call "
                f"drain() or consume events(), give the subscription a "
                f"callback so delivery never queues, or raise "
                f"queue_max=. Dropping the oldest silently is the one "
                f"thing it will not do."
            )
            raise PettaError(
                msg,
                atom=event.atom,
                space=self.space,
            )
        return [*held, event]

    def drain(self) -> list[Event]:
        """Every queued event, oldest first; the queue empties."""
        return self.take()

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
            arrived = self.wait(timeout)
            if not arrived:
                return
            yield from arrived

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, *_exc_info: object) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.cancel()

    def cancel(self) -> None:
        """End the standing query and withdraw its reflection atom."""
        with _TRANSACTION_LOCK:
            cancellation = _REGISTRY.cancel(self)
            if cancellation is not None and self._fact is not None:
                try:
                    if not _has_fact(self._fact):
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


_TRANSACTION_LOCK = threading.RLock()


def _has_fact(fact: Expression) -> bool:
    """Whether another live subscription still owns this reflection atom."""
    return any(
        isinstance(fold, Subscription) and fold._fact == fact
        for fold in _REGISTRY.live()
    )


def _reflection_contains(runtime: Any, fact: Expression) -> bool:
    return runtime.do("petta_py_contains", _REFLECTION_SPACE, fact.to_wire())


def _ensure_reflection_present(runtime: Any, fact: Expression) -> None:
    if not _reflection_contains(runtime, fact):
        _reflect_add(runtime, fact)
    if not _reflection_contains(runtime, fact):
        msg = f"the engine did not retain reflection fact {fact}"
        raise EngineError(msg)


def _ensure_reflection_absent(runtime: Any, fact: Expression) -> None:
    if _reflection_contains(runtime, fact):
        _reflect_remove(runtime, fact)
    if _reflection_contains(runtime, fact):
        msg = f"the engine did not remove reflection fact {fact}"
        raise EngineError(msg)


def _subscriptions_for(space: str) -> tuple[Fold, ...]:
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
    if on not in SubscriptionEdge:
        msg = f"on must be one of {', '.join(SubscriptionEdge)}, not {on!r}"
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
    subscription._fact = Expression([Symbol("subscription"), Symbol(space), pattern, Symbol(on)])
    with _TRANSACTION_LOCK:
        try:
            _ensure_reflection_present(runtime, subscription._fact)
            _REGISTRY.add(runtime, subscription)
        except BaseException as publication_error:
            subscription._active = False
            rollback_errors: list[BaseException] = []
            try:
                if _has_fact(subscription._fact):
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


# ------------------------------------------------------------ bridge rules


def _instantiate(template: Atom, bindings: Mapping[str, Atom]) -> Atom:
    return _map_atoms(
        template,
        lambda atom: bindings.get(atom.name, atom) if isinstance(atom, Variable) else atom,
    )


def bridge(source, pattern, target, template=None, on: str = "add") -> Subscription:
    """A bridge rule between spaces, the multi-context-systems reading:
    when an atom unifying with pattern arrives in source, the template's
    instantiation under the match's bindings lands in target, and with
    on="both" a removal in source removes the instantiation from target,
    the mirrored rule.

        rule = bridge(src, S.alarm(V.zone), dst, S.notify(V.zone))
        src.add(S.alarm(S.kitchen))        # dst now holds (notify kitchen)
        rule.cancel()

    template defaults to the pattern itself. This is the WRITING fold over
    the same event stream the delivering one folds: subscribe's step calls
    your callback, this one's writes, and composing the two is all a bridge
    is. Delivery is inside the write that triggered it; target needs only
    add and remove, so a remote.attach()ed space bridges across engines
    identically.
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
