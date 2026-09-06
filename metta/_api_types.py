"""Purpose: how a space is designated at the API boundary: the identifier types
callers never see, and the one resolution from the receiver a caller holds to
the space a door works in.
Guarantees:
  - type checkers distinguish engine space identifiers from operation names
    without exporting either implementation detail [tested:
    test_canonical_context_types_replace_public_newtypes; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every public door that wants a space takes a context or a space and reaches
    the same space either way [tested:
    test_every_space_door_takes_a_context_or_a_space; commit=WORKTREE]
Assumes:
  - it imports nothing but ``typing``, which is what lets the LEAF modules use
    it: ``metta.casting`` costs 10.9ms to import and ``metta.integrate``, where
    the public ``space_of`` door lives, costs 41.2ms, so a leaf reaching the
    resolution through the satellite would have quadrupled its own import
    [measured 2026-09-06 with ``python -X importtime``; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from typing import Any, Final, NewType

_SpaceId = NewType("_SpaceId", str)
_OperationName = NewType("_OperationName", str)
_DEFAULT_SPACE: Final[_SpaceId] = _SpaceId("&self")


def space_of(m: Any) -> Any:
    """The space a door works in, given a context or a space.

    A door that reads, writes, declares or introspects wants a SPACE, and
    what a caller holds is usually a context. ``MeTTa`` refuses a Space door
    rather than forwarding it, deliberately, so a door written the natural
    way failed on the first storage or introspection door it reached:
    ``metta.lint.lint(m)`` raised ``MeTTa has no 'name'`` and
    ``metta.tables.declare(m, ...)`` raised ``MeTTa has no 'parse'``.

    Duck-typed rather than an isinstance, because the leaf modules that use
    it deliberately do not import the facade. A context is exactly the object
    with a home space to give; a space has none, and answers for itself.

    ``metta.integrate.space_of`` is this resolution's public spelling.
    """
    home = getattr(m, "self", None)
    return m if home is None else home


__all__: list[str] = []
