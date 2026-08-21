"""Purpose: identify the public fields a live Python object can enumerate.
Guarantees:
  - reflective operations and object-space views share one field inventory
    [tested: test_a_query_joins_stored_atoms_with_live_object_fields;
    commit=a3f7e1600b1547617d8be1c365df9c00a74ee81e]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import dataclasses
from typing import Any


def field_names(obj: Any) -> list[str]:
    """Return fields an unbound reflection query may enumerate."""
    if dataclasses.is_dataclass(obj):
        return [field.name for field in dataclasses.fields(obj)]
    if hasattr(obj, "_fields"):
        return list(obj._fields)
    if hasattr(obj, "__dict__"):
        return [name for name in vars(obj) if not name.startswith("_")]
    if hasattr(obj, "__slots__"):
        return [name for name in obj.__slots__ if not name.startswith("_")]
    return []
