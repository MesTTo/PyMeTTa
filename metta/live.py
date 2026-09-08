"""Purpose: `Live`, the materialised view of a query, with the `Delta` stream
its changes arrive on and the three maintenance strategies that keep it
current from the space's own committed writes.

A module of its own, and not a third face in `metta.structures`, because a
program that wants the engine-free stores should not pay to build the view:
defining these classes there cost 0.60% of the structures-dispatch benchmark,
which measures exactly that import [measured 2026-09-07: 597,039,924
instructions against 593,464,324; command=python -m
benchmarks.check_instructions structures-dispatch --rounds 3]. The Python door
is `m.live(*query)`; this module is the class behind it and the longhand its
docstring names.
Assumes:
  - metta.structures owns the atom-kernel helpers this file builds on
    (_as_atom, _canonical) and the tabling call spelling and counters
    (_call_spelling, _table_report), and imports nothing from here at module
    level [source: extensions/python/metta/structures.py:LiveView.__init__;
    commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
Guarantees:
  - a shared table refuses the transactional seed and names the private policy
    [tested: test_a_shared_tabled_view_refuses_its_transactional_seed;
    commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4]
  - Live answers what match answers, through each of its three maintenance
    strategies, and the strategy a query's shape names is the one it gets
    [tested: test_a_pattern_view_holds_the_multiset_through_both_removal_shapes,
    test_a_conjunction_view_re_answers_the_join_on_a_touching_commit,
    test_a_tabled_view_refreshes_after_a_write_to_the_relation,
    test_the_chosen_strategy_is_the_one_the_shape_names; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a pattern view's per-event cost does not move with what it holds, and a
    conjunction view's cost for a write its heads do not name does not either
    [measured 2026-09-08: 90, 90, 90 inferences per touching write over
    relations of 10, 100 and 1,000 against a recompute-per-event consumer's
    178, 553, 4,223, and 95 flat for an untouching write;
    command=python extensions/python/benchmarks/probes/live_view_cost.py --costs;
    fixture=a ring of (edge n_i n_i+1) with (weight n_i i); commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4]
  - a Delta stream delivers a signed multiplicity per row and one progress
    marker per committed segment, and buffers only while it is open [tested:
    test_a_transaction_delivers_one_progress_after_its_deltas,
    test_a_view_matches_a_delta_structurally,
    test_the_async_face_sees_the_same_deltas; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a stream whose buffer is full refuses the write rather than dropping the
    oldest delta, after every other open stream has been offered it [tested:
    test_a_full_changes_stream_does_not_starve_another; commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
  - a view refuses a store that promises no events, a query whose own head is
    an operation that writes, and a tabled strategy with no invalidating table
    behind it [tested: test_a_provider_that_delivers_no_events_refuses_a_view,
    test_a_query_whose_head_writes_refuses,
    test_the_tabled_strategy_refuses_a_head_that_is_not_tabled;
    commit=0de0dc08d2fc77bee9dd132c41f1de23cda1e6c2]
Decides:
  - a live view is keyed by ROWS, and its atom face is derived where the
    query has one atom, because a conjunction answers a row across several
    and a call answers values
  - the tabled strategy's effect gate is the incremental cache policy rather
    than the effect plan's join, because the engine classifies `match` itself
    as writesState and a join-level gate would refuse every real query
    [measured 2026-09-07: a tabled call over a body that matches a space
    answered oracleIO and a bare `(person $n $a)` answered pureStructural;
    command=extensions/python/benchmarks/probes/live_view_cost.py --effects]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading
from collections import Counter, deque
from collections.abc import Iterable, Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from ._api_types import SpaceLike
from .atoms import (
    Atom,
    Expression,
    Symbol,
    Variable,
    _is_ground,
    _match,
    _variables,
    substitute,
)
from .errors import MettaError
from .structures import _as_atom, _call_spelling, _canonical, _table_report
from .vocabularies import DeltaKind, EffectClass, LiveStrategy, SubscriptionEdge

if TYPE_CHECKING:
    from .results import Rows

__all__ = ["Changes", "Delta", "Live"]


def _require_subscribable(space: Any, pattern: Atom, on: str) -> None:
    """Refuse a view of a store whose provider cannot deliver its changes.

    A view is only as current as the events it hears, so a foreign space that
    declares no `subscribe` capability refuses HERE rather than serving a view
    that silently stops tracking. The check is the one `subscribe` itself
    makes, asked in this door's own name.
    """
    from .foreign import require_capability  # noqa: PLC0415 -- avoids a cycle

    require_capability(space.name, "subscribe", "live", pattern=pattern, on=on)


def _writing_head(space: Any, atom: Atom) -> tuple[str, EffectClass] | None:
    """The atom's OWN head, when it is an operation that is not read-only.

    The head and not the join, deliberately, and this is the whole reason the
    refusal is precise rather than universal: the engine classifies `match`
    itself as writesState (resolving a named cast space may create its
    execution module), so every real query's effect plan joins to writesState
    or oracleIO and a join-level gate would refuse every view there is
    [measured 2026-09-07: (cheapest) over a body that matches a space answered
    oracleIO and a bare `(person $n $a)` answered pureStructural;
    command=extensions/python/benchmarks/probes/live_view_cost.py --effects].
    What the operations list DOES say exactly is whether
    the head the caller wrote is itself such an operation, which separates
    `m.live(S["add-atom"](...))` -- a call where a pattern belongs -- from
    `m.live(S.alert(V.l))` in a space that also defines `(= (alert $x)
    (println! $x))`, whose plan names println! and not alert.
    """
    named = _live_head(atom)
    if named is None:
        return None
    head = named[0]
    for name, effect in space.effect_plan(atom).operations:
        if name == head and effect.rank > EffectClass.nondeterministicReadOnly.rank:
            return name, effect
    return None


def _tabled_here(space: Any, named: tuple[str, int]) -> bool:
    """Whether this space has a live tabling declaration for this head.

    lib_tabling reflects every live declaration into `&metta` as
    `(tabled Space Name InputArity)`, so this is one ground containment check
    rather than a query [source: lib/lib_tabling/lib_tabling.pl, "Live
    declarations reflect into &metta as (tabled space name arity) facts"].
    """
    from .ops import _REFLECTION_SPACE  # noqa: PLC0415 -- avoids the ops/structures import cycle

    name, arity = named
    fact = Expression([Symbol("tabled"), Symbol(space.name), Symbol(name), arity])
    return bool(
        space.runtime.do("metta_py_contains", _REFLECTION_SPACE, fact.to_wire())
    )


def _live_strategy(space: Any, atoms: tuple[Atom, ...], strategy: Any) -> LiveStrategy:
    """Which maintenance the view will run, chosen or checked.

    Unchosen, the query's SHAPE decides: one atom whose head is tabled here is
    a call and takes `tabled`, any other single atom is a pattern and takes
    `pattern`, and several atoms are a conjunction and take `heads`.
    """
    named = _live_head(atoms[0]) if len(atoms) == 1 else None
    if strategy is None:
        if named is not None and _tabled_here(space, named):
            return _require_invalidating(space, atoms[0], named)
        chosen = LiveStrategy.pattern if len(atoms) == 1 else LiveStrategy.heads
    else:
        try:
            chosen = LiveStrategy(strategy)
        except ValueError:
            msg = (
                f"strategy must be one of {', '.join(LiveStrategy)}, not "
                f"{strategy!r}"
            )
            raise ValueError(msg) from None
    spelled = " ".join(str(atom) for atom in atoms)
    if chosen is LiveStrategy.pattern and len(atoms) != 1:
        msg = (
            f"the pattern strategy maintains ONE pattern from its own write "
            f"events and this view joins {len(atoms)} ({spelled}); a "
            f"conjunction is re-answered, which is strategy='heads'"
        )
        raise MettaError(msg, space=space.name)
    if chosen is LiveStrategy.tabled:
        if len(atoms) != 1:
            msg = (
                f"the tabled strategy watches ONE call's table and this view "
                f"names {len(atoms)} atoms ({spelled})"
            )
            raise MettaError(msg, space=space.name)
        if named is None or not _tabled_here(space, named):
            call = _call_spelling(*named) if named is not None else spelled
            head = named[0] if named is not None else spelled
            msg = (
                f"the tabled strategy watches a table's invalidation counter "
                f"and {spelled} is not tabled in {space.name}, so there is no "
                f"counter to watch. Declare it with "
                f"!(import! &self (library lib_tabling)) and !(tabled {call}), "
                f"or with a (cache {head} incremental) row in &metta, and the "
                f"view watches the table the declaration builds"
            )
            raise MettaError(msg, atom=atoms[0], space=space.name)
        return _require_invalidating(space, atoms[0], named)
    for atom in atoms:
        writing = _writing_head(space, atom)
        if writing is not None:
            name, effect = writing
            msg = (
                f"a live view re-evaluates its query; {atom} writes "
                f"({name} {effect.value}). A view MATCHES its query against "
                f"stored atoms and never calls it, so a call written where a "
                f"pattern belongs would answer nothing for as long as it "
                f"stands. Table the call and view it as a call "
                f"(!(tabled ...), then m.live(<call>)), or view the pattern "
                f"whose atoms the call would have written"
            )
            raise MettaError(msg, atom=atom, space=space.name)
    return chosen


def _require_invalidating(
    space: Any, atom: Atom, named: tuple[str, int]
) -> LiveStrategy:
    """The tabled strategy, once the policy is one the counter reports on.

    An `incremental` table is invalidated by a write to a space its body
    reads, which is the signal this strategy watches AND the engine's own
    certificate that lib_tabling resolved every one of those reads to a
    watchable native predicate. The other policies answer differently:
    `monotonic` propagates a new fact without invalidating, `plain` watches
    nothing at all, and `lattice` and `subsumptive` are refused a watch on
    this SWI, so under any of them the counter never moves and a view built
    on it would never refresh [source: lib/lib_tabling/lib_tabling.pl, the
    policy guarantees].
    """
    report = _table_report(space, _call_spelling(*named))
    policy = report.get("policy")
    words = (
        [str(word) for word in policy.children]
        if isinstance(policy, Expression)
        else [str(policy)]
    )
    if "incremental" not in words:
        spelled = " ".join(words)
        msg = (
            f"({spelled}) is the cache policy in force for {named[0]}, and its "
            f"re-evaluation does not invalidate: table-stats' invalidated "
            f"counter never moves under it, so a view watching that counter "
            f"would never refresh. Table {named[0]} under incremental (the "
            f"default a bare !(tabled ...) takes), or write the query as the "
            f"patterns it reads and let the heads strategy re-answer it"
        )
        raise MettaError(msg, atom=atom, space=space.name)
    return LiveStrategy.tabled


@dataclass(frozen=True, slots=True)
class Delta:
    """One change to a live view, or the boundary after a commit.

    `kind` is the `delta-kind` vocabulary (`metta.vocabularies.DeltaKind`) and
    `diff` is the signed change in that row's multiplicity: +1, -1, and 0 for a
    progress marker. A member IS its word, so `case Delta("add", ...)` matches
    and `delta.kind == "add"` holds. `row` is the
    answer that changed, keyed by the query's column names, and `atom` is the
    query instantiated under it when the query is ONE atom; a conjunction has
    no single atom and carries None. `generation` is the stream's clock at the
    change.

    A progress delta carries neither row nor atom, and its meaning is only its
    generation: every change committed up to it has already been delivered.
    Materialize's SUBSCRIBE says the same thing in the same shape, a signed
    `mz_diff` per row and `mz_progressed` rows where "everything in the row
    except for mz_timestamp is not a valid update and its content should be
    ignored" [source: https://materialize.com/docs/sql/subscribe/].

    Slotted and frozen, so it matches structurally:

        match delta:
            case Delta("add", _, row, _, _):    arrived(row)
            case Delta("progress", _, _, _, g): current_as_of(g)
    """

    kind: DeltaKind
    diff: int
    row: Mapping[str, Atom] | None
    atom: Atom | None
    generation: int


def _wake(loop: Any, waiter: Any) -> None:
    """Set an async waiter from the writing thread, if one is waiting.

    A consumer whose event loop ended without closing its stream leaves a loop
    that refuses work; the delta is already in the buffer either way, and the
    synchronous face still delivers it, so the wake is dropped rather than
    raised into the write.
    """
    if loop is None or waiter is None:
        return
    with suppress(RuntimeError):
        loop.call_soon_threadsafe(waiter.set)


class Changes:
    """One consumer of a live view's deltas, blocking or async.

    `for delta in live.changes(timeout=1)` sleeps on a condition variable
    between arrivals, and `async for delta in live.changes()` hands the same
    deltas to a running event loop. The stream ends when the view closes, when
    this consumer closes, or when `timeout` seconds pass with nothing arriving.

    Deltas buffer only while a consumer is open, which is what keeps a view
    nobody reads deltas from free; the buffer holds
    `metta.subscribe.queue_bound()` of them and then REFUSES the write
    that would overflow it, the same policy a subscription queue takes and for
    the same reason: dropping the oldest silently is how a gap stays hidden.
    """

    __slots__ = (
        "_bound",
        "_changed",
        "_closed",
        "_live",
        "_loop",
        "_pending",
        "_timeout",
        "_waiter",
    )

    def __init__(
        self, live: Live, timeout: float | None, queue_max: int | None
    ) -> None:
        """Build the consumer; `Live.changes` attaches it."""
        from .subscribe import _capacity  # noqa: PLC0415 -- avoids a cycle

        self._live = live
        self._timeout = timeout
        # None is the standing `(limit subscription-queue ...)` bound, which
        # _capacity resolves; the two consumers share one policy.
        self._bound = _capacity(queue_max)
        self._pending: deque[Delta] = deque()
        self._changed = threading.Condition()
        self._closed = False
        self._loop: Any = None
        self._waiter: Any = None

    def _put(self, delta: Delta) -> None:
        """Take one delta from the writing thread, or refuse to lose it."""
        with self._changed:
            if self._closed:
                return
            if len(self._pending) >= self._bound:
                msg = (
                    f"this changes() consumer holds its limit of {self._bound} "
                    f"undelivered deltas and this one has nowhere to go. "
                    f"Consume the stream, close it, or open it with a larger "
                    f"queue_max=. Dropping the oldest silently is the one "
                    f"thing it will not do."
                )
                raise MettaError(msg, atom=delta.atom, space=self._live.space.name)
            self._pending.append(delta)
            self._changed.notify_all()
            loop, waiter = self._loop, self._waiter
        _wake(loop, waiter)

    def __iter__(self) -> Iterator[Delta]:
        """The stream itself; deltas arrive in the order they were emitted."""
        return self

    def __next__(self) -> Delta:
        """The next delta, blocked until one arrives or the stream ends."""
        with self._changed:
            while not self._pending:
                if self._closed:
                    raise StopIteration
                if not self._changed.wait(self._timeout):
                    raise StopIteration
            return self._pending.popleft()

    def __aiter__(self) -> Self:
        """The stream itself, for `async for`."""
        return self

    async def __anext__(self) -> Delta:
        """The next delta, awaited on the consumer's own running loop."""
        import asyncio  # noqa: PLC0415 -- the async face alone pays for asyncio

        loop = asyncio.get_running_loop()
        while True:
            with self._changed:
                if self._pending:
                    return self._pending.popleft()
                if self._closed:
                    raise StopAsyncIteration
                # The waiter is created and armed under the same lock the
                # writer appends under, so a delta that lands between the
                # empty check and the await sets an event that is already
                # this one rather than being missed.
                waiter = asyncio.Event()
                self._loop, self._waiter = loop, waiter
            try:
                if self._timeout is None:
                    await waiter.wait()
                else:
                    await asyncio.wait_for(waiter.wait(), self._timeout)
            except TimeoutError:
                raise StopAsyncIteration from None
            finally:
                # One waiter per wake, so a delta arriving after this one has
                # a fresh event to set rather than an already-set one.
                with self._changed:
                    if self._waiter is waiter:
                        self._loop, self._waiter = None, None

    def close(self) -> None:
        """Stop buffering and end the stream, here and in the view."""
        with self._changed:
            if self._closed:
                return
            self._closed = True
            self._changed.notify_all()
            loop, waiter = self._loop, self._waiter
            self._loop, self._waiter = None, None
        _wake(loop, waiter)
        self._live._detach(self)

    async def aclose(self) -> None:
        """close(), for a consumer that reached the view through `aio`."""
        self.close()

    def __enter__(self) -> Self:
        """Enter a scope the stream is closed at the end of."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close the stream, whatever the scope did."""
        self.close()

    async def __aenter__(self) -> Self:
        """Enter an async scope the stream is closed at the end of."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Close the stream, whatever the async scope did."""
        self.close()

    def __repr__(self) -> str:
        """Name the buffer's fill against its bound, and the view it reads."""
        return f"Changes({len(self._pending)} of {self._bound} on {self._live!r})"


#: One row as a key, and whether it is ground. A value carrying variables is
#: canonicalized because the engine names a fresh variable per answer while
#: _match names it after the stored atom's own: `(rule $x)` seeds as `($_2,)`
#: and arrives on its removal event as `($_3,)`, and un-canonicalized those are
#: two rows for one atom [measured 2026-09-07;
#: command=extensions/python/benchmarks/probes/live_view_cost.py --naming].
def _live_row(values: Iterable[Atom]) -> tuple[tuple[Atom, ...], bool]:
    key: list[Atom] = []
    ground = True
    for value in values:
        if _variables(value):
            ground = False
            key.append(_canonical(value))
        else:
            key.append(value)
    return tuple(key), ground


def _live_head(atom: Atom) -> tuple[str, int] | None:
    """The head name and input arity of a call-shaped atom, or None."""
    if isinstance(atom, Expression) and atom.children:
        head = atom.children[0]
        if isinstance(head, Symbol):
            return head.name, len(atom.children) - 1
    return None


def _live_watch(atom: Atom) -> Atom:
    """The narrowest subscription pattern this atom could answer through.

    Its head at its arity, or everything when the atom names no head.
    """
    named = _live_head(atom)
    if named is None:
        return Variable("_live")
    name, arity = named
    return Expression(
        [Symbol(name), *(Variable(f"_live{position}") for position in range(arity))]
    )


class Live:
    """A query's answers, materialised and kept current by the space itself.

    Reads are local, because the maintenance already happened.

        alerts = m.live(S.alert(V.level))
        len(alerts)                     # no engine call
        S.alert(S.red) in alerts        # no engine call
        alerts.rows                     # what m.match(...) would answer

    The query is one pattern, a conjunction of patterns spelled the way
    ``match`` spells one, or a call to a TABLED head. Its answers are a
    multiset, as a space is: ``len`` counts occurrences, ``count`` answers a
    multiplicity, and iteration yields rows.

    ``changes()`` is the same view read as a stream of :class:`Delta`, and it
    is where a `progress` marker says which generation the view is current to:

        with alerts.changes(timeout=1) as deltas:
            for delta in deltas:
                match delta:
                    case Delta("add", _, row, _, _):    arrived(row)
                    case Delta("progress", _, _, _, g): current_as_of(g)

    Three maintenance strategies, one meaning. ``strategy=None`` picks by the
    query's shape: ONE atom whose head is tabled in this space takes
    ``tabled``, any other single atom takes ``pattern``, and several atoms take
    ``heads``. ``live.strategy`` names the one in force.

    - ``pattern`` maintains the multiset from the write events themselves,
      O(1) per event and nothing at all per unrelated write. A removal event
      carries the pattern the caller asked for rather than the occurrence that
      left, so it decrements locally when that pattern is ground and the view
      holds no answer with a variable in it, and re-reads the space otherwise.
    - ``heads`` subscribes to every head the query mentions and re-answers the
      whole query once per COMMIT that touched one, diffing the multisets:
      Theta(query) per touching commit, and a transaction of a thousand writes
      is one re-answer rather than a thousand, because the space already held
      the whole diff when its first event arrived.
    - ``tabled`` serves a call by watching its own table: on a touching commit
      it reads ``table-stats``, and re-reads the call only when the
      invalidation counter moved, so a commit that leaves the table valid costs
      the counter and nothing else.

    Refusals. A foreign space that does not declare ``subscribe`` refuses with
    ``SpaceCapabilityError``. A match query whose own head is an operation that
    writes refuses, because a view MATCHES its query and never calls it, so a
    call written where a pattern belongs would materialise nothing forever. A
    ``tabled`` strategy refuses a head that is not tabled, and one whose policy
    does not invalidate, naming the policy. Its atomic seed runs inside a
    transaction, so a shared table is refused by the engine. Declare
    ``(cache f (incremental private))`` in ``&metta`` for a tabled view of ``f``.

    space may be a context or a space.
    """

    def __init__(
        self,
        space: SpaceLike,
        *query: Any,
        on: SubscriptionEdge = SubscriptionEdge.both,
        strategy: str | None = None,
    ) -> None:
        """Choose the maintenance, then seed and install it atomically."""
        home = space.self
        if not query:
            msg = (
                "a live view needs a query: one pattern, a conjunction of "
                "patterns, or a call to a tabled head"
            )
            raise MettaError(msg, space=home.name)
        atoms = tuple(_as_atom(part) for part in query)
        if on not in SubscriptionEdge:
            msg = f"on must be one of {', '.join(SubscriptionEdge)}, not {on!r}"
            raise ValueError(msg)
        _require_subscribable(home, atoms[0], on)
        self._space = home
        self._query = atoms
        self._on = on
        self._strategy = _live_strategy(home, atoms, strategy)
        # The engine names the columns of its own answer, so the view reads
        # them from the first one rather than deriving them a second way that
        # could drift; _open sets them with the seed.
        self._columns: tuple[str, ...] = ()
        self._lock = threading.RLock()
        self._held: Counter[tuple[Atom, ...]] = Counter()
        self._varied = 0
        self._subscriptions: list[Any] = []
        self._consumers: list[Changes] = []
        self._watch: Any = None
        self._stale = False
        # The spelling its counter is read through, taken once: a tabled
        # query has a head, because _live_strategy refuses one that does not.
        named = _live_head(atoms[0])
        self._table = (
            _call_spelling(*named)
            if self._strategy is LiveStrategy.tabled and named is not None
            else ""
        )
        self._invalidated = -1
        self._progress = 0
        self._closed = False
        # Seed and subscribe inside ONE engine transaction, so no write can
        # fall between them: the view starts exactly consistent and every
        # later change arrives as an event. LiveView's rule, and the reason
        # this class does not simply read and then subscribe. A failure part
        # way through takes back what it installed: the transaction rolls the
        # ENGINE back, and a live subscription or segment watch left behind
        # would be a consumer of a view that does not exist.
        try:
            home.transaction(self._open)
        except BaseException:
            self.close()
            raise

    # ------------------------------------------------------------ lifecycle

    def _open(self) -> None:
        """Install the maintenance and take the first answer, atomically."""
        if self._strategy is LiveStrategy.pattern:
            self._subscriptions.append(
                self._space.subscribe(self._query[0], self._deliver, on=self._on)
            )
        else:
            watched: list[Atom] = []
            for atom in self._query:
                # A tabled call's answers move with whatever its BODY reads,
                # which is not its own head, so it watches the whole space.
                shape = (
                    Variable("_live")
                    if self._strategy is LiveStrategy.tabled
                    else _live_watch(atom)
                )
                if not any(shape == seen for seen in watched):
                    watched.append(shape)
            self._subscriptions.extend(
                self._space.subscribe(shape, self._touch, on=self._on)
                for shape in watched
            )
            # A recomputing strategy needs the COMMIT boundary to recompute
            # at, so its watch is not optional; the pattern strategy installs
            # one only while something reads its deltas.
            self._watch = self._space.events().segments(self._boundary)
        self._held, self._varied, self._columns = self._answer()
        self._invalidated = self._invalidations()

    def close(self) -> None:
        """Cancel the maintenance and end every open changes() stream.

        The view keeps its last answer, which is what makes a closed view still
        readable, and stops tracking the space.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            subscriptions, watch = self._subscriptions, self._watch
            consumers = self._consumers
            self._subscriptions, self._watch, self._consumers = [], None, []
        # Every teardown is attempted before any failure is raised: a
        # subscription that refuses to cancel is not a reason to leave the
        # segment watch announcing to nobody.
        failures: list[BaseException] = []
        for close in (
            *(subscription.cancel for subscription in subscriptions),
            *(() if watch is None else (watch.cancel,)),
            *(consumer.close for consumer in consumers),
        ):
            try:
                close()
            except Exception as failure:  # noqa: BLE001  -- every teardown runs before the first failure is raised
                failures.append(failure)
        if failures:
            raise failures[0]

    async def aclose(self) -> None:
        """close(), for a view reached through `aio`."""
        self.close()

    def __enter__(self) -> Self:
        """Enter a scope the view is closed at the end of."""
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Close the view, whatever the scope did."""
        self.close()

    async def __aenter__(self) -> Self:
        """Enter an async scope the view is closed at the end of."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Close the view, whatever the async scope did."""
        self.close()

    # -------------------------------------------------------------- reading

    @property
    def space(self) -> Any:
        """The space this view reads."""
        return self._space

    @property
    def query(self) -> tuple[Atom, ...]:
        """The query as atoms, in the order it was written."""
        return self._query

    @property
    def columns(self) -> tuple[str, ...]:
        """The answer's column names, as `match` names them."""
        return self._columns

    @property
    def strategy(self) -> LiveStrategy:
        """Which maintenance strategy is in force."""
        return self._strategy

    @property
    def rows(self) -> Rows:
        """The current answers, one row per occurrence."""
        # Lazy, because metta.results pulls a display and conversion chain
        # this module is otherwise free of: importing it at the top cost
        # 0.60% of the structures-dispatch benchmark, which pays the import
        # [measured 2026-09-07: 597,042,654 instructions against 593,464,324;
        # command=python -m benchmarks.check_instructions structures-dispatch
        # --rounds 3].
        from .results import Rows  # noqa: PLC0415 -- the display face alone pays

        with self._lock:
            return Rows(self._columns, list(self._held.elements()))

    def atoms(self) -> list[Atom]:
        """The current answers as ATOMS rather than rows.

        The query instantiated under each row, or the call's answers for a
        tabled view. A conjunction has no single atom per row and refuses,
        because inventing one would be a shape the space never held.
        """
        self._require_atom_face("atoms()")
        with self._lock:
            occurrences = list(self._held.elements())
        if self._strategy is LiveStrategy.tabled:
            return [row[0] for row in occurrences]
        return [
            substitute(self._query[0], dict(zip(self._columns, row, strict=True)))
            for row in occurrences
        ]

    def count(self, item: Any) -> int:
        """How many copies of this answer the view holds.

        `item` is an ATOM, read as the query's instantiation (or, for a tabled
        view, as one of the call's answers), or a MAPPING, read as a row keyed
        by the column names.
        """
        key = self._key_of(item)
        if key is None:
            return 0
        with self._lock:
            return self._held.get(key, 0)

    def __contains__(self, item: Any) -> bool:
        """Whether the view holds this answer at all."""
        return self.count(item) > 0

    def __len__(self) -> int:
        """How many answers the view holds, occurrences counted."""
        with self._lock:
            return sum(self._held.values())

    def __iter__(self) -> Iterator[Any]:
        """The current answers, one row per occurrence."""
        return iter(self.rows)

    def _require_atom_face(self, door: str) -> None:
        """Refuse the atom face on a join, which answers rows and no atom."""
        if len(self._query) == 1:
            return
        spelled = " ".join(str(atom) for atom in self._query)
        row = (
            f"live.count({{{self._columns[0]!r}: ...}})"
            if self._columns
            else "live.count(row)"
        )
        msg = (
            f"{door} wants ONE atom per answer and this view joins "
            f"{len(self._query)} patterns ({spelled}), whose answer is a row "
            f"across them rather than an atom the space holds. Read "
            f"live.rows, or ask about a row: {row}"
        )
        raise MettaError(msg, space=self._space.name)

    def _key_of(self, item: Any) -> tuple[Atom, ...] | None:
        """One answer as its multiset key, or None when it cannot be one."""
        if isinstance(item, Mapping):
            missing = [name for name in self._columns if name not in item]
            if missing:
                msg = (
                    f"a row of this view has the columns {list(self._columns)}; "
                    f"{missing} are missing"
                )
                raise MettaError(msg, space=self._space.name)
            return _live_row(_as_atom(item[name]) for name in self._columns)[0]
        atom = _as_atom(item)
        self._require_atom_face("count()")
        if self._strategy is LiveStrategy.tabled:
            return _live_row([atom])[0]
        bindings = _match(self._query[0], atom)
        if bindings is None:
            return None
        return _live_row(
            bindings.get(name, Variable(name)) for name in self._columns
        )[0]

    # ---------------------------------------------------------- maintenance

    def _answer(self) -> tuple[Counter[tuple[Atom, ...]], int, tuple[str, ...]]:
        """The query's answers now, their variety, and their column names.

        The variable count is what keeps the removal fast path sound: with
        none, every answer is ground and a ground removal names exactly the
        occurrence that left. A tabled view answers a CALL, whose answers are
        values rather than bindings, so its one column is `value`, the word
        `eval_status` already uses for the same thing.
        """
        held: Counter[tuple[Atom, ...]] = Counter()
        varied = 0
        if self._strategy is LiveStrategy.tabled:
            columns = ("value",)
            answered: Iterable[Any] = [
                (_as_atom(value),) for value in self._space.eval(self._query[0])
            ]
        else:
            answers = self._space.match(*self._query)
            columns = tuple(answers.columns)
            answered = list(answers)
        for values_of_row in answered:
            key, ground = _live_row(values_of_row)
            held[key] += 1
            if not ground:
                varied += 1
        return held, varied, columns

    def _invalidations(self) -> int:
        """This view's table's invalidation counter, or -1 when it has none."""
        if self._strategy is not LiveStrategy.tabled:
            return -1
        return int(_table_report(self._space, self._table).get("invalidated", 0))

    def _deliver(self, event: Any) -> None:
        """One event, for the pattern strategy: the multiset moves by one."""
        generation = getattr(event, "_generation", 0)
        if event.action == "add":
            key, ground = _live_row(
                event.bindings.get(name, Variable(name)) for name in self._columns
            )
            with self._lock:
                self._held[key] += 1
                if not ground:
                    self._varied += 1
                consumers = bool(self._consumers)
            # The delta's atom is the query instantiated under the row, so
            # building one nobody reads is a substitute() per event.
            if consumers:
                self._emit(
                    Delta(
                        DeltaKind.add, 1, self._row_of(key), self._atom_of(key), generation
                    )
                )
            return
        # A removal event carries the PATTERN asked for, not the occurrence
        # that left, because removal is multiset subtraction and
        # `remove(S.alert(V.q))` takes one of the alerts without saying which.
        # It does say which when that pattern is GROUND and every answer the
        # view holds is ground too: nothing else stored can then unify with
        # it, so exactly one copy of it left and the decrement is local.
        # Anything else re-reads, which is what a handler needing more than
        # the event carries is asked to do.
        key, _ground = _live_row(
            event.bindings.get(name, Variable(name)) for name in self._columns
        )
        with self._lock:
            local = self._varied == 0 and _is_ground(event.atom) and self._held[key] > 0
            if local:
                self._held[key] -= 1
                if self._held[key] <= 0:
                    del self._held[key]
            consumers = bool(self._consumers)
        if local:
            if consumers:
                self._emit(
                    Delta(
                        DeltaKind.remove, -1, self._row_of(key), self._atom_of(key),
                        generation,
                    )
                )
            return
        self._reanswer(generation)

    def _touch(self, _event: Any) -> None:
        """One event, for a recomputing strategy: mark, do not recompute.

        The whole diff is already committed when the first of its events
        arrives, so recomputing here would recompute once per atom over a
        state that is not moving. _boundary is where it happens, once.
        """
        with self._lock:
            self._stale = True

    def _boundary(self, generation: int) -> None:
        """One committed segment has finished.

        Recompute if it touched us, then say which generation this view is
        current to.
        """
        with self._lock:
            stale, self._stale = self._stale, False
            closed = self._closed
        if closed:
            return
        if stale and self._strategy is not LiveStrategy.pattern:
            if self._strategy is LiveStrategy.tabled:
                invalidated = self._invalidations()
                with self._lock:
                    moved = invalidated != self._invalidated
                    self._invalidated = invalidated
                if moved:
                    self._reanswer(generation)
            else:
                self._reanswer(generation)
        with self._lock:
            behind = generation > self._progress
            self._progress = max(self._progress, generation)
        if behind:
            self._emit(Delta(DeltaKind.progress, 0, None, None, generation))

    def _reanswer(self, generation: int) -> None:
        """Re-answer the query and emit the multiset difference.

        A signed multiplicity per row is what a differential engine calls a
        collection of (data, diff) and what Materialize's SUBSCRIBE emits as
        `mz_diff` [source: https://materialize.com/docs/sql/subscribe/].
        """
        held, varied, _columns = self._answer()
        with self._lock:
            before, self._held, self._varied = self._held, held, varied
        if not self._consumers:
            return
        for key in [*held.keys(), *(key for key in before if key not in held)]:
            diff = held.get(key, 0) - before.get(key, 0)
            if diff:
                self._emit(
                    Delta(
                        DeltaKind.add if diff > 0 else DeltaKind.remove,
                        diff,
                        self._row_of(key),
                        self._atom_of(key),
                        generation,
                    )
                )

    # --------------------------------------------------------------- deltas

    def changes(
        self, timeout: float | None = None, *, queue_max: int | None = None
    ) -> Changes:
        """This view's deltas as a stream, blocking or async.

        Deltas buffer only while a stream is open, so a view nobody reads them
        from costs nothing for them. `timeout` (seconds) ends the stream after
        a quiet interval, the way `Subscription.events` does, and `queue_max`
        bounds the buffer, the bound `subscribe` takes and defaulting to the
        same `metta.subscribe.queue_bound()`. A full buffer refuses
        the write that would overflow it rather than dropping the oldest
        delta, and every other open stream is still offered that delta first.
        """
        consumer = Changes(self, timeout, queue_max)
        with self._lock:
            if self._closed:
                msg = "this live view is closed, so it has no more changes to give"
                raise MettaError(msg, space=self._space.name)
            self._consumers.append(consumer)
            if self._watch is None:
                self._watch = self._space.events().segments(self._boundary)
        return consumer

    def _detach(self, consumer: Changes) -> None:
        """Drop one stream, and stop buffering when it was the last."""
        with self._lock:
            self._consumers = [
                current for current in self._consumers if current is not consumer
            ]
            spare = (
                not self._consumers
                and self._strategy is LiveStrategy.pattern
                and self._watch is not None
            )
            watch, self._watch = (self._watch, None) if spare else (None, self._watch)
        if watch is not None:
            watch.cancel()

    def _emit(self, delta: Delta) -> None:
        """Offer one delta to every open stream, then report what refused.

        Every stream is attempted before anything is raised, the rule the
        fold registry already holds for a failed watcher: a full buffer on one
        consumer is not a reason for the others to miss the change.
        """
        with self._lock:
            consumers = tuple(self._consumers)
        refusals: list[Exception] = []
        for consumer in consumers:
            try:
                consumer._put(delta)
            except Exception as refusal:  # noqa: BLE001  -- every stream is offered the delta before any refusal is raised
                refusals.append(refusal)
        if len(refusals) == 1:
            raise refusals[0]
        if refusals:
            msg = (
                f"{len(refusals)} of this view's {len(consumers)} changes() "
                f"streams could not take the {delta.kind} at generation "
                f"{delta.generation}"
            )
            raise ExceptionGroup(msg, refusals)

    def _row_of(self, key: tuple[Atom, ...]) -> Mapping[str, Atom]:
        return dict(zip(self._columns, key, strict=True))

    def _atom_of(self, key: tuple[Atom, ...]) -> Atom | None:
        if len(self._query) != 1:
            return None
        if self._strategy is LiveStrategy.tabled:
            return key[0]
        return substitute(self._query[0], self._row_of(key))

    # -------------------------------------------------------------- display

    def __repr__(self) -> str:
        """Name the query, the space, the strategy and the size."""
        spelled = " ".join(str(atom) for atom in self._query)
        return (
            f"Live({spelled} on {self._space.name}, {self._strategy.value}, "
            f"{len(self)} answers)"
        )

    def _repr_html_(self) -> str:
        """Notebook display: what the view holds, under what it watches."""
        import html  # noqa: PLC0415 -- display alone pays for the escaper

        spelled = html.escape(" ".join(str(atom) for atom in self._query))
        return (
            f"<div><code>live {spelled}</code> on "
            f"<code>{html.escape(str(self._space.name))}</code>, "
            f"<code>{self._strategy.value}</code></div>"
            f"{self.rows._repr_html_()}"
        )
