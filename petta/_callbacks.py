"""Purpose: expose engine callbacks lazily under the ``petta_ops`` alias.

Guarantees:
  - the facade owns no registry state and each callback is the exact object
    from its owning module [tested: test_callback_facade_owns_no_state_and_delegates;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - importing the callback facade does not import event, provider, or path
    satellites [tested: test_m7_satellites_are_lazy_and_identity_stable;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib as _importlib
from typing import Any as _Any

_CALLBACKS = {
    "atom_added": ("events", "atom_added"),
    "atom_removed": ("events", "atom_removed"),
    "construct_token": ("_tokens", "construct_token"),
    "dispatch": ("_ops", "dispatch"),
    "dispatch_inverse": ("_ops", "dispatch_inverse"),
    "dispatch_inverse_raw": ("_ops", "dispatch_inverse_raw"),
    "dispatch_many": ("_ops", "dispatch_many"),
    "dispatch_raw": ("_ops", "dispatch_raw"),
    "dispatch_raw_many": ("_ops", "dispatch_raw_many"),
    "foreign_add": ("foreign", "foreign_add"),
    "foreign_add_many": ("foreign", "foreign_add_many"),
    "foreign_atoms": ("foreign", "foreign_atoms"),
    "foreign_clear": ("foreign", "foreign_clear"),
    "foreign_match": ("foreign", "foreign_match"),
    "foreign_plan": ("foreign", "foreign_plan"),
    "foreign_pushdown": ("foreign", "foreign_pushdown"),
    "foreign_refuse": ("foreign", "foreign_refuse"),
    "foreign_remove": ("foreign", "foreign_remove"),
    "foreign_transaction": ("foreign", "foreign_transaction"),
    "is_matchable": ("foreign", "is_matchable"),
    "match_object": ("foreign", "match_object"),
    "path_begin": ("paths", "_path_begin"),
    "path_step": ("paths", "_path_step"),
    "path_value": ("paths", "_path_value"),
    "type_names": ("_ops", "type_names"),
}

# Names are declared for static tooling but acquire values only through the
# module's PEP 562 resolver.
atom_added: _Any
atom_removed: _Any
construct_token: _Any
dispatch: _Any
dispatch_inverse: _Any
dispatch_inverse_raw: _Any
dispatch_many: _Any
dispatch_raw: _Any
dispatch_raw_many: _Any
foreign_add: _Any
foreign_add_many: _Any
foreign_atoms: _Any
foreign_clear: _Any
foreign_match: _Any
foreign_plan: _Any
foreign_pushdown: _Any
foreign_refuse: _Any
foreign_remove: _Any
foreign_transaction: _Any
is_matchable: _Any
match_object: _Any
path_begin: _Any
path_step: _Any
path_value: _Any
type_names: _Any

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


def __getattr__(name: str) -> _Any:
    """Resolve a callback only when Janus first requests it."""
    try:
        module_name, attribute = _CALLBACKS[name]
    except KeyError:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from None
    module = _importlib.import_module(f"{__package__}.{module_name}")
    value = getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return the exact callback protocol without resolving callbacks."""
    return list(__all__)
