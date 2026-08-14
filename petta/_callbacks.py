"""Purpose: expose Python engine callbacks under the petta_ops import name.
Guarantees:
  - the callback facade owns no registry state and delegates to its owning
    modules [tested test_callback_facade_owns_no_state_and_delegates]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from ._ops import (
    dispatch,
    dispatch_many,
    dispatch_raw,
    dispatch_raw_many,
    type_names,
)
from .foreign import (
    foreign_add,
    foreign_atoms,
    foreign_clear,
    foreign_match,
    foreign_remove,
)
from .subscribe import atom_added, atom_removed

__all__ = [
    "atom_added",
    "atom_removed",
    "dispatch",
    "dispatch_many",
    "dispatch_raw",
    "dispatch_raw_many",
    "foreign_add",
    "foreign_atoms",
    "foreign_clear",
    "foreign_match",
    "foreign_remove",
    "type_names",
]
