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
  - providers may decline one concrete request through should_run before its
    operation executes [tested test_provider_can_decline_one_request]
  - provider registration changes Python state only after the engine accepts
    the same change [tested test_provider_registration_is_transactional]
Guarded by:
  - _PROVIDER_LOCK serializes library registration and provider lookups
    [tested test_provider_registration_is_transactional]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import Any, Protocol, cast, runtime_checkable

from .atoms import Atom, atom_from_wire, encode
from .errors import PettaError

__all__ = [
    "PROVIDERS",
    "Adder",
    "Clearer",
    "Enumerable",
    "Matcher",
    "Remover",
    "SpaceProvider",
    "has_provider",
    "register_provider",
    "require_capability",
    "unregister_provider",
]


@runtime_checkable
class Matcher(Protocol):
    def match(self, pattern: Atom) -> Iterator[Any]: ...


@runtime_checkable
class Enumerable(Protocol):
    def atoms(self) -> Iterator[Any]: ...


@runtime_checkable
class Adder(Protocol):
    def add(self, atom: Atom) -> None: ...


@runtime_checkable
class Remover(Protocol):
    def remove(self, atom: Atom) -> bool: ...


@runtime_checkable
class Clearer(Protocol):
    def clear(self) -> None: ...


class SpaceProvider:
    """One space backed by Python. Implement only what the backend has.

    match(pattern) yields candidate atoms; the pattern's variables arrive as
    Var atoms, and bound positions as ground atoms, which is what a backend
    turns into its own filter (a WHERE clause, a mask). Yielding every atom
    is always correct; yielding fewer than match is never allowed to be.
    An Enumerable provider need not implement Matcher: enumeration is the
    correct default candidate set. Missing methods are unsupported, never
    assumed present.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "capabilities" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__}.capabilities is a stale static declaration; "
                "implement the operation or override can_run() for request-specific policy"
            )

    def can_run(self, capability: str, /, **request: Any) -> bool:
        """Whether this provider implements the operation for this request."""
        if capability == "match":
            return isinstance(self, (Matcher, Enumerable))
        if capability == "enumerate":
            return isinstance(self, Enumerable)
        if capability == "add":
            return isinstance(self, Adder)
        if capability == "remove":
            return isinstance(self, Remover)
        if capability == "clear":
            return isinstance(self, Clearer)
        if capability == "subscribe":
            on = request.get("on", "both")
            if on == "add":
                return isinstance(self, Adder)
            if on == "remove":
                return isinstance(self, Remover)
            return isinstance(self, Adder) and isinstance(self, Remover)
        return False

    def should_run(self, _capability: str, /, **_request: Any) -> bool:
        """Policy hook: decline a supported concrete request before execution."""
        return True

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


def _require_provider(
    provider: SpaceProvider,
    space: str,
    capability: str,
    operation: str,
    **request: Any,
) -> None:
    name = type(provider).__name__
    if not provider.can_run(capability, **request):
        if capability == "enumerate":
            detail = "cannot enumerate atoms"
        elif capability == "subscribe":
            detail = "offers no event source for this subscription"
        else:
            detail = f"does not implement {capability}"
        raise PettaError(
            f"{operation} cannot use {space}: its {name} provider {detail}"
        )
    if not provider.should_run(capability, **request):
        raise PettaError(
            f"{operation} cannot use {space}: its {name} provider declined "
            f"this {capability} request"
        )


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


def register_provider(runtime, name: str, provider: SpaceProvider) -> None:
    if not isinstance(name, str) or not name.startswith("&"):
        raise ValueError(f"a space name starts with &; got {name!r}")
    # Registration is the only place this is cheap to see. Without it an
    # object carrying the narrow protocols but not the base class registers
    # happily, and every later operation dies inside the engine callback on
    # a missing can_run, naming an attribute rather than the mistake.
    missing = [
        method for method in ("can_run", "should_run") if not callable(getattr(provider, method, None))
    ]
    if missing:
        raise TypeError(
            f"a provider answers {' and '.join(missing)}; "
            f"{type(provider).__name__} does not. Subclass petta.foreign."
            f"SpaceProvider, which implements both from the narrow protocols "
            f"the class does provide."
        )
    with _PROVIDER_LOCK:
        holder = _PROVIDERS.get(name)
        if holder is not None and holder is not provider:
            raise ValueError(
                f"{name} already has a provider ({type(holder).__name__}); "
                f"unregister it first, or pick another name. Replacing silently "
                f"would leave the old owner holding a dead registration."
            )
        runtime.must("petta_py_register_foreign(Space)", Space=name)
        _PROVIDERS[name] = provider


def unregister_provider(runtime, name: str) -> None:
    """Release a registered provider; an absent name is a KeyError.

    convert.unregister_type answers the same way. Removing something that
    was never there is a mistake worth hearing about.
    """
    with _PROVIDER_LOCK:
        if name not in _PROVIDERS:
            raise KeyError(f"no provider is registered for {name!r}")
        runtime.must("petta_py_unregister_foreign(Space)", Space=name)
        _PROVIDERS.pop(name, None)


# ------------------------------------------------- called from the shim


def _wire_stream(candidates: Iterable[Any]):
    """Encode candidates lazily, so a large foreign space still streams."""
    for candidate in candidates:
        yield encode(candidate).to_wire()


def foreign_match(space: str, pattern_wire: list):
    """The shim's py_iter enumerates this: candidate atoms, encoded.

    Everything that can fail happens before the generator exists. A
    generator body does not run until the first pull, and an exception
    raised there escapes through py_iter as
    `SystemError: apply_once returned a result with an exception set`,
    which names nothing the caller did. Raising it from an ordinary call
    instead lets janus carry it as the error it is.
    """
    provider = _provider(space)
    pattern = atom_from_wire(pattern_wire)
    _require_provider(provider, space, "match", "match", pattern=pattern)
    if isinstance(provider, Matcher):
        candidates = provider.match(pattern)
    elif isinstance(provider, Enumerable):
        candidates = provider.atoms()
    else:
        raise RuntimeError("validated match provider has no candidate source")
    return _wire_stream(iter(candidates))


def foreign_atoms(space: str):
    """The shim's py_iter enumerates this; see foreign_match on ordering."""
    provider = _provider(space)
    _require_provider(provider, space, "enumerate", "get-atoms")
    return _wire_stream(iter(cast(Enumerable, provider).atoms()))


def foreign_add(space: str, atom_wire: list) -> bool:
    provider = _provider(space)
    atom = atom_from_wire(atom_wire)
    _require_provider(provider, space, "add", "add-atom", atom=atom)
    cast(Adder, provider).add(atom)
    return True


def foreign_remove(space: str, atom_wire: list) -> bool:
    provider = _provider(space)
    atom = atom_from_wire(atom_wire)
    _require_provider(provider, space, "remove", "remove-atom", atom=atom)
    return bool(cast(Remover, provider).remove(atom))


def foreign_clear(space: str) -> bool:
    provider = _provider(space)
    _require_provider(provider, space, "clear", "clear")
    cast(Clearer, provider).clear()
    return True
