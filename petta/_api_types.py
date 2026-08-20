"""Purpose: name the closed and context-sensitive string types in the API.
Guarantees:
  - type checkers distinguish space names from MeTTa function names [tested
    test_public_context_types_are_distinct]
  - SaveFormat admits exactly the two formats save() implements [tested
    test_public_context_types_are_distinct]
  - SaveFormat is generated from the runtime save-format vocabulary rather
    than repeated as an API-local closed list [tested:
    test_a_planted_closed_policy_list_is_reported_by_the_inventory_lane;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from typing import Final, NewType

from .vocabularies import SaveFormat

SpaceName = NewType("SpaceName", str)
MettaName = NewType("MettaName", str)
_DEFAULT_SPACE: Final[SpaceName] = SpaceName("&self")

__all__ = ["MettaName", "SaveFormat", "SpaceName"]
