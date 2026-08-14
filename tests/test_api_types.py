"""Purpose: pin the public contextual names, save format, and constants.
Guarantees:
  - type hints distinguish spaces, MeTTa functions, and save formats [tested
    test_public_context_types_are_distinct]
  - the fixed cache, constructor, and close policies are Final [tested
    test_policy_constants_are_final]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from typing import Final, Literal, get_type_hints

from petta import MeTTa, MettaName, SaveFormat, SpaceName, aio, arrays, space
from petta import _atom_namespace as atom_namespace
from petta._ops import Operation


def test_public_context_types_are_distinct():
    assert SpaceName is not MettaName
    assert SpaceName("&facts") == "&facts"
    assert MettaName("lookup") == "lookup"

    assert get_type_hints(MeTTa.__init__)["space"] is SpaceName
    assert get_type_hints(MeTTa.space)["name"] is SpaceName
    assert get_type_hints(MeTTa.register_op)["name"] == MettaName | None
    assert get_type_hints(Operation)["name"] is MettaName
    assert get_type_hints(Operation)["space"] == SpaceName | None
    assert get_type_hints(MeTTa.save)["format"] == Literal["metta", "fast"]
    assert get_type_hints(aio.AsyncMeTTa.__init__)["space"] is SpaceName
    assert get_type_hints(aio.AsyncMeTTa.save)["format"] == Literal["metta", "fast"]
    assert SaveFormat == Literal["metta", "fast"]


def test_policy_constants_are_final():
    assert get_type_hints(aio)["DEFAULT_CLOSE_TIMEOUT"] == Final[float]
    assert get_type_hints(atom_namespace)["NAMESPACE_CACHE_MAX"] == Final[int]
    assert get_type_hints(arrays)["_CONSTRUCTOR_NAMES"] == Final[tuple[str, ...]]
    assert get_type_hints(space.current_space)["return"] is SpaceName
