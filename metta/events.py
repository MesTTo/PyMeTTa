"""Purpose: the public event stream.

Every committed space write is an event, the stream of `(action, space, atom)`
is a first-class object, and a FOLD over it is the one way to consume it: a step
function `(state, event) -> state` registered for a space and a pattern,
with the accumulated state readable and takeable.

The three models this library ships are that fold with three steps.
`subscribe` folds by delivering, to a callback or to a queue; `bridge`
folds by writing the instantiated template into another space; a declared
`(on ...)` reaction folds by evaluating its operation, engine-side. Before
this the tap was `subscribe._dispatch`, private and "called from the
shim", so a third party could not have written `subscribe()` from the
public surface, and the three siblings were one unnamed family.

Naming the stream and making the tap public is the shape two production
systems already ship. Datomic publishes exactly this: "any peer process in
the system can request a transaction report queue of every transaction
against a particular database", and its stated value is that this "makes
it possible for any peer to observe and respond to transactions ... without
any coordination with database writes", with reactive query notification
left as something you "implement in user space" over it [source: Datomic
blog, The Transaction Report Queue, 11 September 2013; Datomic
Developers forum, "you could use the tx-report-queue or poll the
transaction log to implement one in user space"]. And a fold is the right
consumer because a stream and the state it accumulates are two views of one
thing: Kafka's stream-table duality states that "a stream can be considered
a changelog of a table, where each data record in the stream captures a
state change of the table", and that "aggregating data records in a stream
... will return a table" [source: Apache Kafka, Streams Core Concepts].
Guarantees:
  - unscoped writes publish immediately; transaction and atomic scopes publish
    their ordered diff after commit, while rollback, speculation, and world
    evaluation publish nothing [tested:
    test_events_publish_only_after_transaction_commit,
    test_atomic_scope_commits_or_discards_one_event_segment,
    test_rollback_and_outer_rollback_discard_every_buffered_event,
    test_speculative_execution_discards_its_event_segment; commit=WORKTREE]
  - event attributes project named pattern bindings and unknown names fail as
    attributes [tested: test_take_peek_and_watch_retire_the_thread_linda_fn_strings;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - registry snapshots, fold state and delivery accounting are locked for
    free-threaded Python [tested test_subscription_queue_is_thread_safe,
    test_subscription_cancel_is_thread_safe]
  - dispatch answers the folds on a space in registration order, cancels
    and re-registrations included, through the discrimination tree in
    metta.structures rather than one unify per fold [measured 2026-08-19,
    1000 standing queries on one space and 200 writes, controlled
    instructions:u min of 3: 4012009981 scanning against 48243634 indexed,
    83.2x, both delivering 200 of 200] [tested
    test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order]
  - cancel waits for steps already in flight and a stale dispatch snapshot
    cannot deliver after cancellation [tested
    test_subscription_cancel_waits_for_inflight_delivery,
    test_stale_subscription_snapshot_cannot_deliver_after_cancel]
  - subscribe, bridge and reaction are each expressible as a fold over this
    surface alone, with the same answers as the shipped models [tested
    test_subscribe_bridge_and_reaction_are_expressible_over_the_public_event_stream]
Guarded by:
  - _FoldRegistry._lock protects fold state, the active runtime, delivery
    counts, and engine subscription snapshots [tested
    test_subscription_cancel_is_thread_safe]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final, Self

from .atoms import Atom, _atom_from_wire, _is_ground, _to_atom, unify
from .errors import PettaError, SubscriberError
from .structures import MatchIndex
from .vocabularies import SubscriptionEdge

__all__ = ["STATELESS", "Event", "EventStream", "Fold", "publish", "stream"]


@dataclass(frozen=True)
class Event:
    """One change on the stream.

    What happened, where, to which atom, and with which bindings the watching
    pattern took.
    """

    action: str  # "add" | "remove"
    space: str
    atom: Atom
    bindings: Mapping[str, Atom]

    def __getattr__(self, name: str) -> Atom:
        """Project a watching pattern's binding, as query rows do."""
        try:
            return self.bindings[name]
        except KeyError:
            msg = f"no event binding {name!r}; bindings are {list(self.bindings)}"
            raise AttributeError(msg) from None


#: The step a fold runs per event. It receives the accumulated state and the
#: event and answers the next state, the reducer shape every stream library
#: spells the same way.
Step = Callable[[Any, Event], Any]


class _Stateless:
    """The initial state of a fold that accumulates nothing."""

    __slots__ = ()

    def __repr__(self) -> str:
        """Name the sentinel rather than its address."""
        return "STATELESS"


#: A fold that reacts and accumulates nothing: its step's answer is ignored,
#: take() and wait() answer it back, and, having no state to protect, its
#: steps are NOT serialised against each other, so two writing threads
#: deliver concurrently. Pass any other value, None included, to accumulate.
STATELESS: Final[_Stateless] = _Stateless()


class Fold:
    """One consumer of the stream: a step run for every matching event.

    `cancel()` ends it. `state` is what the steps have accumulated so far,
    `take()` reads it out and starts again from the initial state, which is
    how a queueing consumer is written, and `wait(timeout)` is the same read
    blocked on a condition variable until a step has run.
    """

    __slots__ = (
        "_active",
        "_consumed",
        "_initial",
        "_registry",
        "_state_lock",
        "_step",
        "_version",
        "on",
        "pattern",
        "space",
        "state",
    )

    def __init__(
        self,
        registry: _FoldRegistry,
        space: str,
        pattern: Atom,
        step: Step,
        *,
        on: str,
        state: Any,
    ) -> None:
        """Build the entry; registration is the registry's own step."""
        self._registry = registry
        self.space = space
        self.pattern = pattern
        self.on = on
        self.state = state
        self._initial = state
        self._step = step
        self._active = True
        self._version = 0
        self._consumed = 0
        # State is read-modify-written by every step and reset by every take,
        # so it needs a lock of its own. It cannot be the registry's: a step
        # is user code that may block, and cancel() has to reach the registry
        # while one is in flight, which is exactly what
        # test_subscription_cancel_waits_for_inflight_delivery pins. Lock
        # order is fold before registry, and nothing takes the registry lock
        # and then a fold's. A stateless fold has no read-modify-write at
        # all, so it has no lock and its steps run concurrently.
        self._state_lock = None if state is STATELESS else threading.RLock()

    def cancel(self) -> None:
        """End the fold and wait for steps other threads are still running."""
        self._registry.cancel(self)
        self._registry.wait_for_deliveries(self)

    def take(self) -> Any:
        """The accumulated state, at once, reset to the initial one."""
        return self._registry.take(self)

    def wait(self, timeout: float | None = None) -> Any:
        """The accumulated state, blocked until a step has run.

        Sleeps on a condition variable rather than polling, and returns early
        when the fold cancels or, with a timeout, when the deadline passes.
        Something that arrived before the call is not waited for.
        """
        return self._registry.wait(self, timeout)

    def __enter__(self) -> Self:
        """Enter a scope the fold is cancelled at the end of."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Cancel the fold, whatever the scope did."""
        self.cancel()

    def _run(self, event: Event) -> None:
        """One step, with the in-flight accounting cancel waits on.

        The read of the state, the step, and the write of its answer are one
        locked operation, because they are a read-modify-write: two threads
        delivering to one fold, or a step racing a take(), would otherwise
        each build a next state from the same previous one and the later
        write would erase the earlier. Serial notification per consumer is
        the reactive-streams contract for the same reason [source:
        ReactiveX, Observable Contract: "Observables must issue notifications
        to observers serially, not in parallel"].
        """
        if not self._registry.begin_delivery(self):
            return
        try:
            if self._state_lock is None:
                # Nothing to accumulate, so nothing to serialise and nothing
                # for a waiter to read. This is the delivering fold, the one
                # subscribe() builds for a callback, and it pays exactly what
                # the bespoke dispatch it replaced paid.
                self._step(STATELESS, event)
                return
            with self._state_lock:
                before = self.state
                after = self._step(before, event)
                if self.state is not before and self.state is not after:
                    msg = (
                        f"the fold on {self.pattern} in {self.space} wrote an "
                        f"atom its own pattern matches, so its step ran again "
                        f"inside itself and finished first. Keeping this "
                        f"step's answer would erase the nested one and "
                        f"keeping the nested one would erase this. Write into "
                        f"a different space, narrow the pattern, or accumulate "
                        f"in an object the step mutates instead of a value it "
                        f"replaces."
                    )
                    raise PettaError(msg, atom=event.atom, space=self.space)
                self.state = after
                self._version += 1
            # Waking is for wait(), and most folds have no waiter: a callback
            # subscription never has one. The version is bumped ABOVE this
            # read, and a waiter increments the count and then checks that
            # same version under the registry lock, so a count read as zero
            # proves the waiter has not checked yet and will see the bump.
            # Notifying unconditionally cost one lock acquisition and a
            # notify_all per delivery [measured 2026-08-21, 1000 standing
            # queries and 200,000 taps, instructions:u min of 3: 120,409 per
            # delivery against 115,745 with this gate, 4.0%].
            if self._registry.waiters:
                self._registry.arrived()
        finally:
            self._registry.end_delivery(self)


@dataclass(frozen=True)
class _Cancellation:
    runtime: Any
    order: tuple[Fold, ...]
    index: int


class _FoldRegistry:
    """Every live fold, in registration order, indexed per space."""

    def __init__(self) -> None:
        """Start with nothing watching and no runtime claimed."""
        self._lock = threading.RLock()
        self._delivery_changed = threading.Condition(self._lock)
        self._arrived = threading.Condition(self._lock)
        self._folds: list[Fold] = []
        self._deliveries: dict[Fold, dict[int, int]] = {}
        # One discrimination tree per space, so N stays per-space exactly as
        # the scan's own space filter made it.
        self._indexes: dict[str, MatchIndex] = {}
        #: How many threads are inside wait(). Read without the lock on the
        #: delivery path; see Fold._run for why that is race-free.
        self.waiters = 0
        self.runtime = None

    def add(self, runtime, fold: Fold) -> None:
        """Publish a fold, or leave the registry exactly as it was."""
        with self._lock:
            if self.runtime is not None and self.runtime is not runtime:
                msg = "subscriptions cannot span distinct engine runtimes in one process"
                raise RuntimeError(
                    msg
                )
            if any(current is fold for current in self._folds):
                msg = "the subscription is already registered"
                raise RuntimeError(msg)
            candidate = [*self._folds, fold]
            self._publish_locked(runtime, candidate)
            self.runtime = runtime
            self._folds = candidate
            self._indexes.setdefault(fold.space, MatchIndex()).add(fold.pattern, fold)

    def cancel(self, fold: Fold) -> _Cancellation | None:
        """Withdraw a fold; an already-cancelled one answers None."""
        with self._lock:
            if not fold._active:
                return None
            index = next(
                (
                    position
                    for position, current in enumerate(self._folds)
                    if current is fold
                ),
                None,
            )
            if index is None:
                msg = "an active subscription is missing from the registry"
                raise RuntimeError(msg)
            if self.runtime is None:
                msg = "the subscription registry has no engine runtime"
                raise RuntimeError(msg)
            order = tuple(self._folds)
            candidate = self._folds.copy()
            candidate.pop(index)
            self._publish_locked(self.runtime, candidate)
            self._folds = candidate
            fold._active = False
            tree = self._indexes.get(fold.space)
            if tree is not None:
                tree.remove(fold.pattern, fold)
            self._arrived.notify_all()  # blocking takes end at cancel
            return _Cancellation(self.runtime, order, index)

    def restore(self, cancellation: _Cancellation, fold: Fold) -> None:
        """Put a cancelled fold back where it was, for a failed rollback."""
        with self._lock:
            if fold._active or any(current is fold for current in self._folds):
                msg = "cannot restore an active subscription"
                raise RuntimeError(msg)
            if self.runtime is not cancellation.runtime:
                msg = "cannot restore a subscription on another runtime"
                raise RuntimeError(msg)
            candidate = self._folds.copy()
            candidate.insert(self._restoration_index(cancellation), fold)
            self._publish_locked(cancellation.runtime, candidate)
            self._folds = candidate
            fold._active = True
            # Restoration puts a fold back where it WAS, so appending to the
            # tree would file it last. Rebuilding the one space's tree from
            # the restored order is the only spelling that keeps delivery
            # order equal to registration order, and this is the rollback
            # path, where O(N) is not the concern.
            self._rebuild_locked(fold.space)

    def arrived(self) -> None:
        """Wake every waiter, a step having just moved some fold on."""
        with self._lock:
            self._arrived.notify_all()

    def take(self, fold: Fold) -> Any:
        """The accumulated state, reset, without waiting."""
        if fold._state_lock is None:
            return STATELESS
        with fold._state_lock:
            state, fold.state = fold.state, fold._initial
            fold._consumed = fold._version
            return state

    def wait(self, fold: Fold, timeout: float | None) -> Any:
        """The accumulated state, blocked until a step has run.

        The condition is shared, so a wake for another fold re-checks against
        the remaining deadline. A step that ran BEFORE this call already
        moved the version past what the last take consumed, so an arrival
        that beat the waiter is answered rather than waited for; the counter
        is bumped under the fold's own lock and the wake is sent under this
        one, which is what makes that check race-free rather than lucky.
        """
        if fold._state_lock is None:
            # A stateless fold never moves, so waiting for it to move would
            # be waiting forever. Answering at once says "there is nothing
            # here to read" rather than hanging on it.
            return STATELESS
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._lock:
            self.waiters += 1
            try:
                while fold._active and fold._version == fold._consumed:
                    if deadline is None:
                        self._arrived.wait()
                        continue
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._arrived.wait(remaining)
            finally:
                self.waiters -= 1
        return self.take(fold)

    def live(self) -> tuple[Fold, ...]:
        """Every live fold, whatever its space, in registration order."""
        with self._lock:
            return tuple(fold for fold in self._folds if fold._active)

    def begin_delivery(self, fold: Fold) -> bool:
        """Claim one in-flight step, or refuse because the fold is cancelled."""
        with self._lock:
            if not fold._active:
                return False
            thread_id = threading.get_ident()
            counts = self._deliveries.setdefault(fold, {})
            counts[thread_id] = counts.get(thread_id, 0) + 1
            return True

    def end_delivery(self, fold: Fold) -> None:
        """Release one in-flight step and wake anything waiting for it."""
        with self._lock:
            thread_id = threading.get_ident()
            counts = self._deliveries.get(fold)
            if counts is None or counts.get(thread_id, 0) == 0:
                msg = "subscription delivery accounting is unbalanced"
                raise RuntimeError(msg)
            if counts[thread_id] == 1:
                del counts[thread_id]
            else:
                counts[thread_id] -= 1
            if not counts:
                del self._deliveries[fold]
            self._delivery_changed.notify_all()

    def wait_for_deliveries(self, fold: Fold) -> None:
        """Wait for other threads; a step may cancel its own fold safely."""
        thread_id = threading.get_ident()
        with self._delivery_changed:
            self._delivery_changed.wait_for(
                lambda: (
                    not any(
                        owner != thread_id and count
                        for owner, count in self._deliveries.get(fold, {}).items()
                    )
                )
            )

    def for_space(self, space: str) -> tuple[Fold, ...]:
        """Every live fold on one space, in registration order."""
        with self._lock:
            return tuple(
                fold
                for fold in self._folds
                if fold._active and fold.space == space
            )

    def candidates(self, space: str, atom: Atom) -> tuple[Fold, ...]:
        """The folds on this space whose pattern could match the atom.

        In registration order.

        A superset of the ones that WILL match is all this owes: the caller
        unifies anyway, because it needs the bindings. What it owes exactly
        is the order and the completeness.

        A probe carrying variables goes down the list instead. The tree reads
        probe tokens literally, so a variable in the probe would need every
        edge followed at once, and MatchIndex answers that by scanning its
        whole entry table and sorting it, which is more work than the list
        this registry already keeps in order. An atom with variables in it is
        a real thing to store, `(rule $x)` reads back as `(rule $_608)`, so
        this is a shape the write path meets rather than one it can refuse.
        """
        with self._lock:
            if not _is_ground(atom):
                return tuple(
                    fold
                    for fold in self._folds
                    if fold._active and fold.space == space
                )
            tree = self._indexes.get(space)
            if tree is None:
                return ()
            return tuple(fold for _pattern, fold in tree.matches(atom))

    def _rebuild_locked(self, space: str) -> None:
        tree = MatchIndex()
        for fold in self._folds:
            if fold._active and fold.space == space:
                tree.add(fold.pattern, fold)
        self._indexes[space] = tree

    def _publish_locked(self, runtime: Any, folds: list[Fold]) -> None:
        current_spaces = self._spaces(self._folds)
        candidate_spaces = self._spaces(folds)
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
            for index, current in enumerate(self._folds):
                if current is successor:
                    return index
        for predecessor in reversed(cancellation.order[: cancellation.index]):
            for index, current in enumerate(self._folds):
                if current is predecessor:
                    return index + 1
        return min(cancellation.index, len(self._folds))

    @staticmethod
    def _spaces(folds: list[Fold]) -> list[str]:
        return sorted({fold.space for fold in folds})


_REGISTRY = _FoldRegistry()


class EventStream:
    """The engine's `(action, space, atom)` stream, as an object.

        events = m.events()
        seen = events.fold(
            lambda held, event: [*held, event.atom],
            space=m.name, pattern=S.order(V.id), state=[],
        )
        m.add(S.order(1))
        seen.take()            # [(order 1)], and the fold starts again

    One operation, `fold`, plus `publish` for a provider whose own channel
    carries changes this process did not make. Everything else this library
    offers over events is a fold with a different step, so a third party's
    consumer and a shipped one are the same kind of thing.
    """

    __slots__ = ("_runtime",)

    def __init__(self, runtime: Any) -> None:
        """Bind the stream to one engine runtime."""
        self._runtime = runtime

    def fold(
        self,
        step: Step,
        *,
        space: str,
        pattern: Any,
        on: str = "add",
        state: Any = STATELESS,
    ) -> Fold:
        """Run `step(state, event)` for every matching change to `space`.

        `pattern` selects the events by unification, and its bindings ride on
        each event. `on` is "add", "remove" or "both". `state` is where the
        fold starts and what `take()` resets it to; the step's answer is the
        next state. Leave `state` alone and the fold accumulates nothing,
        which is what a consumer that only reacts wants and what costs it no
        serialisation. An unscoped write runs steps synchronously before it
        returns. A transactional write runs them synchronously after the
        complete commit, so every step reads committed state; rollback,
        speculation, and world evaluation run none. A step may write back and
        an infinite add-triggers-add loop is the author's own.
        """
        if on not in SubscriptionEdge:
            msg = f"on must be one of {', '.join(SubscriptionEdge)}, not {on!r}"
            raise ValueError(
                msg
            )
        fold = Fold(_REGISTRY, space, _to_atom(pattern), step, on=on, state=state)
        _REGISTRY.add(self._runtime, fold)
        return fold

    def folds(self, space: str) -> tuple[Fold, ...]:
        """Every live fold on one space, in registration order."""
        return _REGISTRY.for_space(space)

    def publish(self, action: str, space: str, atom: Any) -> None:
        """Announce a change this process did not write.

        The engine's own write hooks publish every write it makes. A provider
        whose store also changes elsewhere and that has a channel saying so,
        Redis pub/sub or PostgreSQL LISTEN/NOTIFY, announces those changes
        here, which is what its `(events ...)` declaration promised.
        """
        if action not in ("add", "remove"):
            msg = f"action is 'add' or 'remove', not {action!r}"
            raise ValueError(msg)
        _deliver(action, space, _to_atom(atom))


def stream(runtime: Any) -> EventStream:
    """The event stream of one engine; `MeTTa.events()` is the usual door."""
    return EventStream(runtime)


# ------------------------------------------------- called from the shim


def publish(action: str, space: str, wire: list) -> bool:
    """The engine's write hooks, arriving as events.

    Public because the stream is: a host binding for another language taps in
    here exactly as the Python shim does.
    """
    _deliver(action, space, _atom_from_wire(wire))
    return True


def _deliver(action: str, space: str, atom: Atom) -> None:
    for fold in _REGISTRY.candidates(space, atom):
        if fold.on not in ("both", action):
            continue
        bindings = unify(fold.pattern, atom)
        if bindings is None:
            continue
        try:
            fold._run(Event(action, space, atom, bindings))
        # A control signal is BaseException and passes through untouched:
        # KeyboardInterrupt is not a watcher saying no.
        except Exception as failure:
            msg = (
                f"{space} applied and committed the {action} of {atom}, then a watcher "
                f"failed. This is not a failed write: retrying it may store a "
                f"second copy, because a space is a multiset. Transactional "
                f"watchers run only after commit and cannot roll that commit "
                f"back. "
                f"Delivering to the subscription on {fold.pattern} "
                f"raised {type(failure).__name__}: {failure}"
            )
            raise SubscriberError(
                msg,
                subscription=fold,
                action=action,
                atom=atom,
                space=space,
            ) from failure


def atom_added(space: str, wire: list) -> bool:
    """The shim's added-atom hook."""
    return publish("add", space, wire)


def atom_removed(space: str, wire: list) -> bool:
    """The shim's removed-atom hook."""
    return publish("remove", space, wire)
