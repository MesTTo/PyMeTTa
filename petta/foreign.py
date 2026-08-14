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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Iterator
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

    def should_run(self, capability: str, /, **request: Any) -> bool:
        """Policy hook: decline a supported concrete request before execution."""
        return True

    def supports(self, capability: str, /, **request: Any) -> bool:
        """Compatibility spelling for can_run()."""
        return self.can_run(capability, **request)


# space name (with &) -> provider; consulted by the shim's foreign hooks
# through the petta_ops module functions below.
PROVIDERS: dict[str, SpaceProvider] = {}


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
    provider = PROVIDERS.get(space)
    if provider is None:
        return
    _require_provider(provider, space, capability, operation, **request)


def register_provider(runtime, name: str, provider: SpaceProvider) -> None:
    if not name.startswith("&"):
        raise ValueError(f"a space name starts with &; got {name!r}")
    holder = PROVIDERS.get(name)
    if holder is not None and holder is not provider:
        raise ValueError(
            f"{name} already has a provider ({type(holder).__name__}); "
            f"unregister it first, or pick another name. Replacing silently "
            f"would leave the old owner holding a dead registration."
        )
    PROVIDERS[name] = provider
    runtime.must("petta_py_register_foreign(Space)", Space=name)


def unregister_provider(runtime, name: str) -> None:
    PROVIDERS.pop(name, None)
    runtime.must("petta_py_unregister_foreign(Space)", Space=name)


# ------------------------------------------------- called from the shim


def foreign_match(space: str, pattern_wire: list):
    """Generator the shim's py_iter enumerates: candidate atoms, encoded."""
    provider = PROVIDERS[space]
    pattern = atom_from_wire(pattern_wire)
    _require_provider(provider, space, "match", "match", pattern=pattern)
    if isinstance(provider, Matcher):
        candidates = provider.match(pattern)
    elif isinstance(provider, Enumerable):
        candidates = provider.atoms()
    else:
        raise RuntimeError("validated match provider has no candidate source")
    for candidate in candidates:
        yield encode(candidate).to_wire()


def foreign_atoms(space: str):
    provider = PROVIDERS[space]
    _require_provider(provider, space, "enumerate", "get-atoms")
    for atom in cast(Enumerable, provider).atoms():
        yield encode(atom).to_wire()


def foreign_add(space: str, atom_wire: list) -> bool:
    provider = PROVIDERS[space]
    atom = atom_from_wire(atom_wire)
    _require_provider(provider, space, "add", "add-atom", atom=atom)
    cast(Adder, provider).add(atom)
    return True


def foreign_remove(space: str, atom_wire: list) -> bool:
    provider = PROVIDERS[space]
    atom = atom_from_wire(atom_wire)
    _require_provider(provider, space, "remove", "remove-atom", atom=atom)
    return bool(cast(Remover, provider).remove(atom))


def foreign_clear(space: str) -> bool:
    provider = PROVIDERS[space]
    _require_provider(provider, space, "clear", "clear")
    cast(Clearer, provider).clear()
    return True
