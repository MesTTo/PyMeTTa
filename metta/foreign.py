"""Purpose: spaces implemented in Python. A SpaceProvider answers match, add,
remove and enumeration for a named space whose atoms live wherever the
provider keeps them: a SQL table, a dataframe, a dict, a service. The engine
unifies patterns against what the provider yields, so a provider may
over-approximate its filtering and stay sound; pushing bound parts of the
pattern down into the backend is the performance lever, never a correctness
requirement.
Guarantees:
  - capabilities derive from implemented narrow protocols and unknown
    operations are refused [tested test_capabilities_follow_implemented_methods]
  - subscribability is not derived: a provider declares what its change
    events promise through delivers(), registration publishes that as the
    space's (events ...) row, and one that declares nothing refuses a
    subscription naming the missing capability [tested
    test_a_context_that_declares_events_serves_them_and_one_that_does_not_refuses]
  - providers may decline one concrete request through should_run before its
    operation executes [tested test_provider_can_decline_one_request]
  - provider registration changes Python state only after the engine accepts
    the same change [tested test_provider_registration_is_transactional]
  - a provider's own refusal sentence reaches the caller, and "implements it
    and declines it" reads differently from "does not have it" [tested
    test_a_provider_states_its_own_refusal,
    test_declining_and_not_implementing_read_differently]
  - a declined capability is checked where it is USED, so match's fall-through
    to enumeration consults enumerate [tested
    test_a_declined_enumerate_is_not_reached_through_match]
  - a single-pattern bounded query tells a provider whose match takes a limit
    keyword how many answers the caller keeps, never sends it across a join,
    and bounds the answers itself whatever the provider does [tested
    2026-08-16: test_a_bound_reaches_a_provider_that_takes_one,
    test_a_bound_is_not_pushed_past_a_join,
    test_a_provider_ignoring_the_bound_is_still_bounded_by_the_engine]
  - the caller's bound reaches a provider that claimed its filtering exact
    for that pattern and is withheld from one that claimed nothing, so a
    provider cannot truncate to a number it never promised it could use, and
    a false claim is caught by check_space_provider rather than by an answer
    going missing [tested test_a_bound_is_withheld_from_a_provider_that_claimed_nothing,
    test_a_bound_reaches_a_provider_that_takes_one,
    test_a_false_exact_claim_is_caught]
  - provider length exists only through Python's Sized protocol and never
    falls back to enumeration [tested:
    test_provider_length_requires_and_uses_sized; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - snapshot capability is structural and explicit, so reification never
    mistakes live enumeration for an immutable view [tested:
    test_reify_refuses_and_names_a_live_composite_member; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Guarded by:
  - _PROVIDER_LOCK serializes library registration and provider lookups
    [tested test_provider_registration_is_transactional]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
import threading
from collections.abc import Iterable, Iterator, Mapping, Sized
from functools import cache
from types import MappingProxyType
from typing import Any, ClassVar, Protocol, cast, runtime_checkable

from .answer import Answer
from .atoms import Atom, Box, Expression, Grounded, Symbol, _atom_from_wire, _encode
from .errors import PettaError, TransportFailure, is_transport_failure
from .vocabularies import Delivery, EventOrder

__all__ = [
    "CAPABILITIES",
    "PROVIDERS",
    "Adder",
    "BoundedMatcher",
    "BulkAdder",
    "Clearer",
    "CustomMatch",
    "Enumerable",
    "MatchClassifier",
    "Matcher",
    "Planner",
    "Remover",
    "Snapshotter",
    "SpaceProvider",
    "Transactional",
    "WorldCommitter",
    "delivery_promise",
    "has_provider",
    "register_provider",
    "require_capability",
    "unregister_provider",
]


#: Every operation the seam names, in the engine's own vocabulary.
#:
#: `rules` is the odd one and the one that matters most: it says this space's
#: atoms include EQUATIONS, which in MeTTa is the difference between a data
#: source and a place a program lives. The provider stores one the way it
#: stores any atom and the ENGINE compiles it, so a rule here is the same
#: compiled clause a native one is. It is opt-in because no protocol can
#: derive a promise about content from a method.
CAPABILITIES = (
    "match", "enumerate", "add", "add-many", "remove", "clear", "subscribe",
    "plan", "rules",
)


@runtime_checkable
class Matcher(Protocol):  # noqa: D101  -- the Protocol methods below are the searchable contract for this structural type
    def match(self, pattern: Atom) -> Iterator[Any]: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


class BoundedMatcher(Protocol):
    """A Matcher whose match also takes the caller's bound.

    `limit` is how many answers the caller will keep. It is advisory, and
    that is what makes it sound: a provider may over-approximate, so N
    candidates are not N answers, and truncating at N without knowing which
    candidates unify would yield fewer answers than exist. Honour it only
    where an exact match is distinguishable from a candidate; ignoring it is
    always correct, because the engine bounds the answers itself.

    Deliberately not runtime_checkable. A Protocol's isinstance looks at
    method NAMES only, so it would answer True for every Matcher; the
    signature is what separates the two, and _match_takes_a_bound reads it.
    """

    def match(self, pattern: Atom, *, limit: int | None = None) -> Iterator[Any]: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class CustomMatch(Protocol):
    """A grounded value that owns its matching logic, Hyperon's CustomMatch.

    Any object whose class defines `match_` participates in `(unify ...)`
    the moment it appears as an operand or inside one, with no
    registration, exactly as any grounded atom. `match_(other)` receives
    the atom the value met and yields one item per binding set: a
    `Bindings` or `Answer` binding `other`'s variables, a plain atom or
    value the operand must equal, or nothing at all for no match. This is
    the same answer stream a provider's match yields, so residues and
    explicit values work; an annotation is refused, because a bare value
    has no context to declare a semiring on, and weighted matching
    belongs to a registered context. In Hyperon a space is exactly such a
    value whose match_ is query, which is why `unify` accepts spaces.
    """

    def match_(self, other: Atom) -> Iterable[Any]: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class MatchClassifier(Protocol):
    """A Matcher that says how good its own filtering is, for one pattern.

    Answer `"exact"` when every candidate you yield for this pattern unifies
    with it, so N candidates are N answers and you may truncate to a limit.
    Answer `"inexact"` otherwise, which is what a provider without this method
    is taken to mean and is always safe.

    Per PATTERN, not per provider, which is the part worth having: a backend
    is usually exact on equality against an indexed column and inexact on
    everything else, and one flag for the whole provider would force it to
    claim the weaker answer everywhere.

    This is Apache DataFusion's TableProviderFilterPushDown, whose Exact rung
    reads "Your source guarantees that no output rows will have a false value
    for this predicate", against Inexact, "Your source has the ability to
    reduce the data produced, but the output may still include rows that do
    not satisfy the predicate" [source: Apache DataFusion, Custom Table
    Providers]. Spark's DataSourceV2 draws the same line as "filters that need
    to be evaluated after scanning" against those that do not
    [source: Apache Spark 4.2.0 Java API, SupportsPushDownFilters.pushFilters,
    "Pushes down filters, and returns filters that need to be evaluated after
    scanning"].

    DataFusion's third rung, Unsupported, is absent here. It exists there
    because the planner decides whether to SEND a filter at all; the pattern
    is the only thing a provider is given, so there is nothing to withhold,
    and a provider that ignores it is inexact in the only sense that acts on
    anything.

    A wrong "exact" costs answers, so check_space_provider tests the claim
    against the provider's own output.
    """

    def pushdown(self, pattern: Atom) -> str: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Transactional(Protocol):
    """A provider that participates in the engine's transactions.

    Declared with (writes <ctx> transactional) or ``space.writes``: the
    engine calls begin() at the provider's first write inside the
    outermost transaction, then exactly one of commit() or rollback()
    when it finishes, alongside the engine's own database rollback, so a
    MeTTa (transaction ...) is atomic across both stores.
    """

    def begin(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
    def commit(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
    def rollback(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Enumerable(Protocol):  # noqa: D101  -- the Protocol methods below are the searchable contract for this structural type
    def atoms(self) -> Iterator[Any]: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Snapshotter(Protocol):
    """A provider that captures one immutable atom tuple at one instant."""

    def snapshot(self) -> tuple[Atom, ...]:
        """Capture one immutable atom tuple at one instant."""


@runtime_checkable
class WorldCommitter(Protocol):
    """A provider that lands one checked base-relative world diff.

    The provider owns the atomic boundary because only it can keep its
    external store and durable log under one lock. The caller publishes the
    returned diff to the ordinary post-commit event stream only after this
    method succeeds.
    """

    def commit_world(
        self,
        base: tuple[Atom, ...],
        removed: list[Atom],
        added: list[Atom],
    ) -> None:
        """Land one base-relative diff under the provider's atomic boundary."""


@runtime_checkable
class Adder(Protocol):  # noqa: D101  -- the Protocol methods below are the searchable contract for this structural type
    def add(self, atom: Atom) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Planner(Protocol):
    """A whole conjunction, offered before the engine splits it.

    Return None to decline, which is what a provider without a join should do
    and what every provider written before this does by not implementing it.
    Otherwise return (claimed, rest, rows): the patterns you took, the ones you
    left for the engine, and the rows. `claimed` and `rest` must partition the
    conjunction, because the engine plans only what you leave and a dropped
    pattern stops constraining the query. Each row is a list of instantiated
    atoms, one per claimed pattern, in the order you claimed them.

    A claim is EXACT, which is the one place this seam differs from the rest of
    it. Elsewhere you may over-approximate because the engine re-unifies each
    candidate cheaply; there is no cheap re-check for a join, so a provider that
    cannot answer exactly must decline.
    """

    def plan(  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self, patterns: list[Atom]
    ) -> tuple[list[Atom], list[Atom], Iterator[Any]] | None: ...
    # A row is a list of instantiated atoms, one per claimed pattern, or a
    # metta.Answer whose theta binds the claimed patterns' own variables
    # directly, which deletes the per-row re-unification atom rows force.


@runtime_checkable
class BulkAdder(Protocol):
    """A whole batch in one crossing, for a backend that can take one.

    Optional. Without it a batch is one `add(atom)` per atom, which is what
    every provider written before this gets. A batch is a transport
    optimisation and never a semantic one, so the engine sends only atoms
    whose add is a store and nothing more: an equation or a type declaration
    anywhere in the list drops the whole batch to the per-atom path and never
    reaches here.
    """

    def add_many(self, atoms: list[Atom]) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Remover(Protocol):  # noqa: D101  -- the Protocol methods below are the searchable contract for this structural type
    def remove(self, atom: Atom) -> bool: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


@runtime_checkable
class Clearer(Protocol):  # noqa: D101  -- the Protocol methods below are the searchable contract for this structural type
    def clear(self) -> None: ...  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract


class SpaceProvider:
    """One space backed by Python. Implement only what the backend has.

    match(pattern) yields candidate atoms; the pattern's variables arrive as
    Variable atoms, and bound positions as ground atoms, which is what a backend
    turns into its own filter (a WHERE clause, a mask). Yielding every atom
    is always correct; yielding fewer than match is never allowed to be.
    An Enumerable provider need not implement Matcher: enumeration is the
    correct default candidate set. Missing methods are unsupported, never
    assumed present.

    A variable's NAME does not survive the crossing, and this is the place
    that will surprise you. `$x` arrives as `$_17902`, because a variable is
    an identity rather than a spelling and the engine renames on the way in.
    Fuzzing the round trip with 500 examples found the rename in 174 of them
    and nothing else: ground atoms are exact in both directions, and what a
    provider stores comes back to it unchanged. It is not a seam defect, the
    native path does the same, but a provider that PERSISTS atoms persists the
    renamed form, and a rule editor, a serializer or a diff built on this will
    meet it. If you need the source spelling, keep it yourself.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        super().__init_subclass__(**kwargs)
        if "capabilities" in cls.__dict__:
            msg = (
                f"{cls.__name__}.capabilities is a stale static declaration; "
                "implement the operation or override can_run() for request-specific policy"
            )
            raise TypeError(
                msg
            )

    #: The narrow protocol each capability needs, in the engine's vocabulary.
    #: `rules` is absent on purpose: it is a promise about what the space
    #: HOLDS, not a method it implements, so no protocol can derive it and a
    #: provider says yes by overriding can_run.
    _PROTOCOLS: ClassVar[dict[str, tuple[type, ...]]] = {
        "match": (Matcher, Enumerable),
        "enumerate": (Enumerable,),
        "add": (Adder,),
        "add-many": (BulkAdder,),
        "plan": (Planner,),
        "remove": (Remover,),
        "clear": (Clearer,),
    }

    def delivers(self) -> tuple[str, str] | None:
        """What this space's change events promise, or None for no events.

        `(delivery, order)` from the catalog's own words: delivery is
        "at-most-once", "at-least-once" or "per-write-exactly", and order is
        "ordered" or "unordered". Registration writes the answer into &petta
        as `(events <space> <delivery> <order>)`, so a MeTTa program reads
        the same promise the engine acts on.

        None is the default and it is the safe one. Whether a space can emit
        change events is a promise about the SPACE, not something the seam
        can read off the methods: a store whose every write comes through
        this engine gets per-write-exactly for free from the engine's own
        write hooks, and one whose contents also change elsewhere gets
        nothing unless it has a channel of its own. Deriving it from add and
        remove made a remote space claim events it could not deliver, and a
        watcher heard this process's own writes and missed every other one.
        Say what your channel promises, or say nothing and subscriptions are
        refused with your own words.
        """
        return None

    def can_run(self, capability: str, /, **request: Any) -> bool:
        """Whether this provider implements the operation for this request."""
        protocols = self._PROTOCOLS.get(capability)
        if protocols is not None:
            return isinstance(self, protocols)
        if capability == "subscribe":
            return self._can_subscribe(request.get("on", "both"))
        # `rules` and anything unknown: opt in by overriding. It is a promise
        # about what the space HOLDS: say yes and an equation added here is
        # compiled by the engine, say nothing and one is refused at add-atom.
        return False

    def _can_subscribe(self, on: str) -> bool:
        """A declared event capability, narrowed to the edge asked for.

        Two questions, both required. The declaration says the space can
        emit change events at all; the write protocol says which EDGE it can
        produce, since a store with no remove never emits a removal and a
        watcher for one would wait forever.
        """
        if delivery_promise(self) is None:
            return False
        if on == "add":
            return isinstance(self, Adder)
        if on == "remove":
            return isinstance(self, Remover)
        return isinstance(self, Adder) and isinstance(self, Remover)

    def should_run(self, _capability: str, /, **_request: Any) -> bool:
        """Policy hook: decline a supported concrete request before execution."""
        return True

    def refusal(self, _capability: str, /, **_request: Any) -> str | None:
        """Why this provider says no, in its own words.

        can_run() and should_run() carry a boolean and no reason, so the
        refusal had to be built from the capability name and got it wrong:
        a provider that IMPLEMENTS add and declines it was told it "does not
        implement add", and the message saying what to do instead, which the
        provider had already written, was unreachable. Return a sentence and
        it is used verbatim; return None and the generic wording applies.
        """
        return None

    def supports(self, capability: str, /, **request: Any) -> bool:
        """Compatibility spelling for can_run()."""
        return self.can_run(capability, **request)


# Space name (with &) -> provider; consulted by the shim's foreign hooks
# through the petta_ops module functions below. The public view is read-only
# so registration cannot bypass the engine transaction or its lock.
_PROVIDERS: dict[str, SpaceProvider] = {}
PROVIDERS: Mapping[str, SpaceProvider] = MappingProxyType(_PROVIDERS)
_PROVIDER_LOCK = threading.RLock()


def _provider(space: str) -> SpaceProvider:
    with _PROVIDER_LOCK:
        return _PROVIDERS[space]


def has_provider(space: str) -> bool:
    """Whether a Python provider currently owns the space."""
    with _PROVIDER_LOCK:
        return space in _PROVIDERS


def _provider_length(space: str) -> int | None:
    """A declared provider length, or None when this is not a provider space.

    ``Sized`` is Python's structural declaration for ``__len__``. Enumerating
    an arbitrary backend here would turn an absent complexity promise into a
    potentially remote full scan merely because a caller wrote ``len(space)``.
    """
    with _PROVIDER_LOCK:
        provider = _PROVIDERS.get(space)
    if provider is None:
        return None
    if not isinstance(provider, Sized):
        msg = (
            f"len({space}) is unavailable: {type(provider).__name__} does not "
            f"implement __len__; counting by enumeration would hide the "
            f"provider's cost"
        )
        raise TypeError(msg)
    return len(provider)


def _require_provider(
    provider: SpaceProvider,
    space: str,
    capability: str,
    operation: str,
    **request: Any,
) -> None:
    if provider.can_run(capability, **request) and provider.should_run(
        capability, **request
    ):
        return
    name = type(provider).__name__
    stated = _stated_refusal(provider, capability, request)
    if stated is not None:
        msg = f"{operation} cannot use {space}, whose {name} provider says: {stated}"
        raise PettaError(
            msg,
            space=space,
            operation=operation,
            capability=capability,
        )
    msg = (
        f"{operation} cannot use {space}: its {name} provider "
        f"{_refusal_detail(provider, capability, request)}"
    )
    raise PettaError(
        msg,
        space=space,
        operation=operation,
        capability=capability,
    )


def _stated_refusal(
    provider: SpaceProvider, capability: str, request: dict[str, Any]
) -> str | None:
    """The provider's own sentence, when it wrote one."""
    hook = getattr(provider, "refusal", None)
    if not callable(hook):
        return None
    stated = hook(capability, **request)
    return stated if isinstance(stated, str) and stated else None


def _refusal_detail(
    provider: SpaceProvider, capability: str, request: dict[str, Any]
) -> str:
    """Implementing an operation and declining it are different things.

    "does not implement add" was said to a provider that implements add and
    returns False from can_run, which is factually wrong and hides the
    distinction the model already draws. The base class's own can_run is the
    test for "is it there at all", so calling it unbound answers that
    independently of whatever the subclass decided.
    """
    if SpaceProvider.can_run(provider, capability, **request):
        return f"declines this {capability} request"
    if capability == "enumerate":
        return "cannot enumerate atoms"
    if capability == "subscribe":
        if delivery_promise(provider) is None:
            return (
                "declares no event capability: override delivers() to return "
                "one of the catalog's delivery promises, or leave it None and "
                "poll the space instead"
            )
        return "offers no event source for this subscription"
    return f"does not implement {capability}"


def require_capability(
    space: str,
    capability: str,
    operation: str,
    **request: Any,
) -> None:
    """Refuse an operation before it creates partial state or enters Prolog."""
    with _PROVIDER_LOCK:
        provider = _PROVIDERS.get(space)
    if provider is None:
        return
    _require_provider(provider, space, capability, operation, **request)


def register_provider(runtime, name: str, provider: SpaceProvider) -> None:  # noqa: D103  -- the package reference and enclosing module document this exported entry point
    if not isinstance(name, str) or not name.startswith("&"):
        msg = f"a space name starts with &; got {name!r}"
        raise ValueError(msg)
    # Registration is the only place this is cheap to see. Without it an
    # object carrying the narrow protocols but not the base class registers
    # happily, and every later operation dies inside the engine callback on
    # a missing can_run, naming an attribute rather than the mistake.
    missing = [
        method for method in ("can_run", "should_run") if not callable(getattr(provider, method, None))
    ]
    if missing:
        msg = (
            f"a provider answers {' and '.join(missing)}; "
            f"{type(provider).__name__} does not. Subclass metta.foreign."
            f"SpaceProvider, which implements both from the narrow protocols "
            f"the class does provide."
        )
        raise TypeError(
            msg
        )
    with _PROVIDER_LOCK:
        holder = _PROVIDERS.get(name)
        if holder is not None and holder is not provider:
            msg = (
                f"{name} already has a provider ({type(holder).__name__}); "
                f"unregister it first, or pick another name. Replacing silently "
                f"would leave the old owner holding a dead registration."
            )
            raise ValueError(
                msg
            )
        # The engine's own vocabulary, computed here because this is where
        # it already was. Without it foreign_provides/2 reported that every
        # Python provider provides everything, so anything the engine decides
        # from a declaration excluded exactly the incomplete providers.
        # The event promise rides the same crossing rather than a second one:
        # it is written as the space's ordinary (events ...) declaration, and
        # a re-registration that stops promising events has to stop the space
        # being subscribable in the same step.
        promise = delivery_promise(provider)
        runtime.must(
            "petta_py_register_foreign(Space, Capabilities, Delivery)",
            Space=name,
            Capabilities=[c for c in CAPABILITIES if provider.can_run(c)],
            Delivery=list(promise) if promise is not None else [],
        )
        _PROVIDERS[name] = provider


def unregister_provider(runtime, name: str) -> None:
    """Release a registered provider; an absent name is a KeyError.

    convert.unregister_type answers the same way. Removing something that
    was never there is a mistake worth hearing about.
    """
    with _PROVIDER_LOCK:
        if name not in _PROVIDERS:
            msg = f"no provider is registered for {name!r}"
            raise KeyError(msg)
        runtime.must("petta_py_unregister_foreign(Space)", Space=name)
        _PROVIDERS.pop(name, None)


# ------------------------------------------------- called from the shim


def _wire_stream(candidates: Iterable[Any], *, answers: bool = True):
    """Encode candidates lazily, so a large foreign space still streams.

    A match stream may carry explicit answers beside plain atoms; an
    enumeration may not, because there is no query whose variables a
    binding could name.
    """
    iterator = iter(candidates)
    while True:
        try:
            candidate = next(iterator)
        except StopIteration:
            return
        except Exception as error:
            # Classified at the crossing, where isinstance still sees the
            # real class: a transport failure re-raises under the seam's
            # own name, so the engine's declared error modes can hold the
            # trichotomy without parsing Python class names.
            if not isinstance(error, TransportFailure) and is_transport_failure(error):
                raise TransportFailure(str(error)) from error
            raise
        if isinstance(candidate, Answer):
            if not answers:
                msg = (
                    "atoms() yielded an Answer; an enumeration has no query "
                    "to bind, so it yields atoms only"
                )
                raise PettaError(
                    msg
                )
            yield candidate.to_wire()
        else:
            yield _encode(candidate).to_wire()


@cache
def _match_takes_a_bound(provider_type: type) -> bool:
    """Whether this provider's match() accepts a limit keyword.

    Discovered from the signature, the way can_run() discovers the narrow
    protocols, so a provider written before this is called exactly as it was.
    Cached on the type: the answer cannot change for a class, and asking
    inspect once per match would put signature parsing on the query path.
    """
    match = getattr(provider_type, "match", None)
    if match is None:
        return False
    try:
        parameters = inspect.signature(match).parameters
    except (TypeError, ValueError):
        # A C-implemented or otherwise unintrospectable match: call it the
        # old way rather than guess at a signature.
        return False
    limit = parameters.get("limit")
    return limit is not None and limit.kind in (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def _candidates_from_matcher(provider: Matcher, pattern: Atom, limit: int | None):
    """A provider's match, given the caller's bound when it takes one.

    The bound is advisory. A provider may over-approximate, so N candidates
    are not N answers, and one that truncated at N without knowing which of
    its candidates unify would under-answer, which the contract forbids.
    Honour it only where an exact match is distinguishable, and ignore it
    otherwise: the engine bounds the answers itself, so ignoring it is
    always correct and only leaves the backend doing more work.
    """
    if limit is None or not _match_takes_a_bound(type(provider)):
        return provider.match(pattern)
    return cast("BoundedMatcher", provider).match(pattern, limit=limit)


def delivery_promise(provider: Any) -> tuple[str, str] | None:
    """A provider's declared event capability, checked against the catalog.

    Silence is None and means no events, which is the safe answer and what
    every provider that says nothing gets. A claim outside the catalog's own
    `delivery` and `event-order` vocabularies is a mistake worth hearing
    about rather than a value to fall back from: falling back would either
    invent a promise the author did not make or discard one they did.
    """
    if not callable(getattr(provider, "delivers", None)):
        return None
    claimed = provider.delivers()
    if claimed is None:
        return None
    if (
        not isinstance(claimed, tuple)
        or len(claimed) != 2
        or claimed[0] not in Delivery
        or claimed[1] not in EventOrder
    ):
        msg = (
            f"{type(provider).__name__}.delivers() answered {claimed!r}; it is "
            f"None for a space with no change events, or a pair "
            f"(delivery, order) with delivery one of {', '.join(Delivery)} and "
            f"order one of {', '.join(EventOrder)}"
        )
        raise PettaError(msg)
    return claimed


def pushdown_class(provider: Any, pattern: Atom) -> str:
    """What a provider claims about its filtering for this pattern.

    Silence is "inexact", which is Prolog's closed-world reading of the same
    question and the cautious answer: an inexact provider's candidates are
    re-unified and its bound stays advice. A claim that is neither word is a
    mistake worth hearing about rather than a value to fall back from,
    because the fallback would silently discard a real "exact".
    """
    if not isinstance(provider, MatchClassifier):
        return "inexact"
    claimed = provider.pushdown(pattern)
    if claimed not in ("exact", "inexact"):
        msg = (
            f"{type(provider).__name__}.pushdown({pattern!r}) answered "
            f"{claimed!r}; it is 'exact' when every candidate you yield for "
            f"this pattern unifies with it, and 'inexact' otherwise"
        )
        raise PettaError(
            msg
        )
    return claimed


def foreign_refuse(space: str, capability: str) -> None:
    """Raise this provider's own refusal for a capability it does not provide.

    The engine now knows what a Python provider provides, so its own
    refuse_absent_capability/2 fires FIRST for an absent capability, and the
    provider's sentence would be lost behind a generic permission_error. This
    hands the refusal back to the side that has the words: "does not implement
    add" and "declines this add request" read differently, and a provider that
    wrote its own reason gets to say it.

    It never returns. Returning would mean the engine and this side disagree
    about what the provider provides, which is exactly the split the
    capability projection closed.
    """
    provider = _provider(space)
    _require_provider(provider, space, capability, capability)
    msg = (
        f"{space} refused {capability} to the engine and allows it here; the "
        f"engine's capability record and this provider disagree"
    )
    raise PettaError(
        msg,
        space=space,
        capability=capability,
    )


def foreign_pushdown(space: str, pattern_wire: list) -> str:
    """The shim asks this before pulling a bounded match's candidates."""
    provider = _provider(space)
    return pushdown_class(provider, _atom_from_wire(pattern_wire))


def _erring_stream(stream, mode: str, pattern):
    """Enforce a declared error mode where the exceptions are native.

    A mid-iteration exception tunnels through py_iter past every Prolog
    catch, so keep and empty are enforced HERE: keep yields the failure as
    the reserved ["x","error",...] item carrying the language's own
    (Error <query> <reason>) atom, empty ends the stream, and both always
    end with ["x","end"] so an empty stream still claims the route.
    Control signals and transport failures re-raise, always.
    """
    # KeyboardInterrupt and SystemExit are BaseException, outside this
    # handler by construction, so control signals pass through untouched.
    try:
        yield from stream
    except Exception as error:
        if isinstance(error, TransportFailure):
            raise
        if is_transport_failure(error):
            raise TransportFailure(str(error)) from error
        if mode == "keep":
            reason = f"{type(error).__name__}: {error}"
            kept = Expression([Symbol("Error"), pattern, Grounded(reason)])
            yield ["x", "error", kept.to_wire()]
    yield ["x", "end"]


def foreign_match(
    space: str, pattern_wire: list, limit: int | None = None, mode: str = "abort"
):
    """The shim's py_iter enumerates this: candidate atoms, encoded.

    Everything that can fail happens before the generator exists. A
    generator body does not run until the first pull, and an exception
    raised there escapes through py_iter as
    `SystemError: apply_once returned a result with an exception set`,
    which names nothing the caller did. Raising it from an ordinary call
    instead lets janus carry it as the error it is.
    """
    provider = _provider(space)
    pattern = _atom_from_wire(pattern_wire)
    _require_provider(provider, space, "match", "match", pattern=pattern)
    if isinstance(provider, Matcher):
        candidates = _candidates_from_matcher(provider, pattern, limit)
    elif isinstance(provider, Enumerable):
        # The declared capability, checked where it is USED. A provider
        # allowing match and declining enumerate ("queries yes, full dumps
        # no") had atoms() called anyway, because only the match capability
        # was consulted and the fall-through went straight past the one it
        # was about to use.
        _require_provider(provider, space, "enumerate", "match", pattern=pattern)
        candidates = provider.atoms()
    else:
        msg = "validated match provider has no candidate source"
        raise RuntimeError(msg)  # noqa: TRY004  -- the provider failed after dispatch, so this is an execution failure rather than caller type validation
    stream = _wire_stream(iter(candidates))
    if mode == "abort":
        return stream
    return _erring_stream(stream, mode, pattern)


def foreign_atoms(space: str):
    """The shim's py_iter enumerates this; see foreign_match on ordering."""
    provider = _provider(space)
    _require_provider(provider, space, "enumerate", "get-atoms")
    return _wire_stream(iter(cast(Enumerable, provider).atoms()), answers=False)


def is_matchable(obj: Any) -> bool:
    """Whether a grounded value owns its matching logic; the shim's probe."""
    return callable(getattr(_unwrap_box(obj), "match_", None))


def match_object(obj: Any, other_wire: list):
    """One grounded value's match_ against the operand it met in unify.

    The value is local, so nothing crosses per candidate: match_ runs
    here and only the answers are encoded. Errors abort by design; see
    CustomMatch.
    """
    other = _atom_from_wire(other_wire)
    return _wire_stream(iter(_unwrap_box(obj).match_(other)))


def _unwrap_box(obj: Any) -> Any:
    return obj.value if isinstance(obj, Box) else obj


def foreign_transaction(space: str, step: str) -> bool:
    """One transactional step on a declared-transactional provider."""
    provider = _provider(space)
    if not isinstance(provider, Transactional):
        msg = (
            f"{space} is declared (writes {space} transactional) and its "
            f"provider {type(provider).__name__} does not implement "
            f"begin/commit/rollback; implement metta.foreign.Transactional "
            f"or declare best-effort"
        )
        raise PettaError(
            msg
        )
    getattr(provider, step)()
    return True


def foreign_add(space: str, atom_wire: list) -> bool:
    provider = _provider(space)
    atom = _atom_from_wire(atom_wire)
    _require_provider(provider, space, "add", "add-atom", atom=atom)
    cast(Adder, provider).add(atom)
    return True


def foreign_plan(space: str, pattern_wires: list):
    """The claim, as the shim asks for it: a decline is `None`, a claim is
    [claimed, rest, rows] on the wire. The rows are materialised here rather
    than streamed, because a claim is answered as a whole and the engine has no
    use for a half-planned join.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    provider = _provider(space)
    patterns = [_atom_from_wire(wire) for wire in pattern_wires]
    if not isinstance(provider, Planner) or not provider.should_run(
        "plan", patterns=patterns
    ):
        return None
    claim = provider.plan(patterns)
    if claim is None:
        return None
    claimed, rest, rows = claim
    return [
        [atom.to_wire() for atom in claimed],
        [atom.to_wire() for atom in rest],
        [
            row.to_wire()
            if isinstance(row, Answer)
            else [atom.to_wire() for atom in row]
            for row in rows
        ],
    ]


def foreign_add_many(space: str, atom_wires: list) -> bool:
    provider = _provider(space)
    atoms = [_atom_from_wire(wire) for wire in atom_wires]
    _require_provider(provider, space, "add", "add-atom", atom=atoms[0])
    cast(BulkAdder, provider).add_many(atoms)
    return True


def foreign_remove(space: str, atom_wire: list) -> bool:
    provider = _provider(space)
    atom = _atom_from_wire(atom_wire)
    _require_provider(provider, space, "remove", "remove-atom", atom=atom)
    return bool(cast(Remover, provider).remove(atom))


def foreign_clear(space: str) -> bool:
    provider = _provider(space)
    _require_provider(provider, space, "clear", "clear")
    cast(Clearer, provider).clear()
    return True
