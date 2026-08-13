"""Purpose: spaces implemented in Python. A SpaceProvider answers match, add,
remove and enumeration for a named space whose atoms live wherever the
provider keeps them: a SQL table, a dataframe, a dict, a service. The engine
unifies patterns against what the provider yields, so a provider may
over-approximate its filtering and stay sound; pushing bound parts of the
pattern down into the backend is the performance lever, never a correctness
requirement.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Iterator

from .atoms import Atom, encode, from_wire

__all__ = ["SpaceProvider", "PROVIDERS", "register_provider", "unregister_provider"]

# space name (with &) -> provider; consulted by the shim's foreign hooks
# through the petta_ops module functions below.
PROVIDERS: dict[str, "SpaceProvider"] = {}


class SpaceProvider:
    """One space backed by Python. Subclass and override what the backend has.

    match(pattern) yields candidate atoms; the pattern's variables arrive as
    Var atoms, and bound positions as ground atoms, which is what a backend
    turns into its own filter (a WHERE clause, a mask). Yielding every atom
    is always correct; yielding fewer than match is never allowed to be.
    A provider without add/remove is read-only, and the engine's write
    answers a clear error instead of pretending.
    """

    def match(self, pattern: Atom) -> Iterator[Any]:
        """Candidates for a pattern; the default enumerates everything."""
        return self.atoms()

    def atoms(self) -> Iterator[Any]:
        raise NotImplementedError(f"{type(self).__name__} does not enumerate")

    def add(self, atom: Atom) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only: no add")

    def remove(self, atom: Atom) -> bool:
        raise NotImplementedError(f"{type(self).__name__} is read-only: no remove")


def register_provider(runtime, name: str, provider: SpaceProvider) -> None:
    if not name.startswith("&"):
        raise ValueError(f"a space name starts with &; got {name!r}")
    PROVIDERS[name] = provider
    runtime.must("petta_py_register_foreign(Space)", Space=name)


def unregister_provider(runtime, name: str) -> None:
    PROVIDERS.pop(name, None)
    runtime.must("petta_py_unregister_foreign(Space)", Space=name)


# ------------------------------------------------- called from the shim


def foreign_match(space: str, pattern_wire: list):
    """Generator the shim's py_iter enumerates: candidate atoms, encoded."""
    provider = PROVIDERS[space]
    pattern = from_wire(pattern_wire)
    for candidate in provider.match(pattern):
        yield encode(candidate).to_wire()


def foreign_atoms(space: str):
    provider = PROVIDERS[space]
    for atom in provider.atoms():
        yield encode(atom).to_wire()


def foreign_add(space: str, atom_wire: list) -> bool:
    PROVIDERS[space].add(from_wire(atom_wire))
    return True


def foreign_remove(space: str, atom_wire: list) -> bool:
    return bool(PROVIDERS[space].remove(from_wire(atom_wire)))
