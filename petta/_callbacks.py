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
    dispatch_inverse,
    dispatch_inverse_raw,
    dispatch_many,
    dispatch_raw,
    dispatch_raw_many,
    type_names,
)
from .foreign import (
    foreign_add,
    foreign_add_many,
    foreign_atoms,
    foreign_clear,
    foreign_match,
    foreign_plan,
    foreign_pushdown,
    foreign_refuse,
    foreign_remove,
    foreign_transaction,
    is_matchable,
    match_object,
)
from .subscribe import atom_added, atom_removed

__all__ = [
    "atom_added",
    "atom_removed",
    "dispatch",
    "dispatch_inverse",
    "dispatch_inverse_raw",
    "dispatch_many",
    "dispatch_raw",
    "dispatch_raw_many",
    "foreign_add",
    "foreign_add_many",
    "foreign_atoms",
    "foreign_clear",
    "foreign_match",
    "foreign_plan",
    "foreign_pushdown",
    "foreign_refuse",
    "foreign_remove",
    "foreign_transaction",
    "is_matchable",
    "match_object",
    "type_names",
]
