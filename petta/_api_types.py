"""Purpose: name the closed and context-sensitive string types in the API.
Guarantees:
  - type checkers distinguish space names from MeTTa function names [tested
    test_public_context_types_are_distinct]
  - SaveFormat admits exactly the two formats save() implements [tested
    test_public_context_types_are_distinct]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from typing import Final, Literal, NewType, TypeAlias

SpaceName = NewType("SpaceName", str)
MettaName = NewType("MettaName", str)
SaveFormat: TypeAlias = Literal["metta", "fast"]
_DEFAULT_SPACE: Final[SpaceName] = SpaceName("&self")

__all__ = ["MettaName", "SaveFormat", "SpaceName"]
