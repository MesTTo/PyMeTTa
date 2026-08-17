"""Purpose: public two-way conversion facade and registration API.
Guarantees:
  - public names preserve the petta.convert import surface after directional
    module cuts [tested test_build_reverses_the_projection,
    test_registered_custom_type_round_trips]
  - type registrations can be removed without leaving constructor or name
    ownership behind [tested
    test_type_registration_can_be_removed_and_its_name_reclaimed]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from ._convert_build import build
from ._convert_project import Projected, auto_image, declarations, project
from ._convert_registry import (
    IMAGES,
    ensure_registered,
    register_type,
    unregister_type,
)
from ._convert_registry import (
    _is_plain_class as _registry_is_plain_class,
)

_is_plain_class = _registry_is_plain_class

Projected.__module__ = __name__

__all__ = [
    "IMAGES",
    "Projected",
    "auto_image",
    "build",
    "declarations",
    "ensure_registered",
    "project",
    "register_type",
    "unregister_type",
]
