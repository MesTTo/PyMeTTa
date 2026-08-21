"""Purpose: expose Python engine callbacks under the petta_ops import name.
Guarantees:
  - the callback facade owns no registry state and delegates to its owning
    modules, including reader-token construction [tested:
    test_callback_facade_owns_no_state_and_delegates; commit=2c741dda928a30d0ce1c7e1fcf0b263b4d1bb97b]
  - lazy path callbacks retain an opaque root and project one segment per
    crossing [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=a1b10566194f10c174101fdc05f956b33171613b]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from ._ops import (
    dispatch,
    dispatch_inverse,
    dispatch_inverse_raw,
    dispatch_many,
    dispatch_raw,
    dispatch_raw_many,
    type_names,
)
from ._tokens import construct_token
from .events import atom_added, atom_removed
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

__all__ = [
    "atom_added",
    "atom_removed",
    "construct_token",
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
