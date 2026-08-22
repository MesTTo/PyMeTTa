"""Purpose: keep implementation-only identifier types out of the public API.
Guarantees:
  - type checkers distinguish engine space identifiers from operation names
    without exporting either implementation detail [tested:
    test_canonical_context_types_replace_public_newtypes; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from typing import Final, NewType

_SpaceId = NewType("_SpaceId", str)
_OperationName = NewType("_OperationName", str)
_DEFAULT_SPACE: Final[_SpaceId] = _SpaceId("&self")

__all__: list[str] = []
