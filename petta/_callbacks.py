"""Purpose: expose Python engine callbacks under the petta_ops import name.
Guarantees:
  - the callback facade owns no registry state and delegates to its owning
    modules [tested test_callback_facade_owns_no_state_and_delegates]
  - lazy path callbacks retain an opaque root and project one segment per
    crossing [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=WORKTREE]
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
from .paths import _path_begin as path_begin
from .paths import _path_step as path_step
from .paths import _path_value as path_value
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
    "path_begin",
    "path_step",
    "path_value",
    "type_names",
]
