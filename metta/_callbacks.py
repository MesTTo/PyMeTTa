"""Purpose: expose engine callbacks lazily under the ``petta_ops`` alias.

Guarantees:
  - the facade owns no registry state and each callback is the exact object
    from its owning module [tested: test_callback_facade_owns_no_state_and_delegates;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - importing the callback facade does not import event, provider, or path
    satellites [tested: test_m7_satellites_are_lazy_and_identity_stable;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - scheduler context and async-operation callbacks resolve lazily to their
    owning satellites [tested:
    test_context_snapshot_crosses_every_spawn_door_including_thread_workers,
    test_an_async_operation_answers_a_future_space; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import importlib as _importlib
from typing import Any as _Any

_CALLBACKS = {
    "async_cancel": ("_async_ops", "cancel"),
    "async_discard": ("_async_ops", "discard"),
    "async_prepare": ("_async_ops", "prepare"),
    "async_start": ("_async_ops", "start"),
    "atom_added": ("events", "atom_added"),
    "atom_removed": ("events", "atom_removed"),
    "capture_context": ("_task_context", "snapshot"),
    "capture_contexts": ("_task_context", "snapshot_many"),
    "construct_token": ("_tokens", "construct_token"),
    "dispatch": ("_ops", "dispatch"),
    "dispatch_context": ("_ops", "dispatch_context"),
    "dispatch_inverse": ("_ops", "dispatch_inverse"),
    "dispatch_inverse_context": ("_ops", "dispatch_inverse_context"),
    "dispatch_inverse_raw": ("_ops", "dispatch_inverse_raw"),
    "dispatch_inverse_raw_context": ("_ops", "dispatch_inverse_raw_context"),
    "dispatch_many": ("_ops", "dispatch_many"),
    "dispatch_many_context": ("_ops", "dispatch_many_context"),
    "dispatch_raw": ("_ops", "dispatch_raw"),
    "dispatch_raw_context": ("_ops", "dispatch_raw_context"),
    "dispatch_raw_many": ("_ops", "dispatch_raw_many"),
    "dispatch_raw_many_context": ("_ops", "dispatch_raw_many_context"),
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
    "fork_context": ("_task_context", "fork"),
    "fork_contexts": ("_task_context", "fork_many"),
    "is_matchable": ("foreign", "is_matchable"),
    "match_object": ("foreign", "match_object"),
    "path_begin": ("paths", "_path_begin"),
    "path_step": ("paths", "_path_step"),
    "path_value": ("paths", "_path_value"),
    "release_context": ("_task_context", "release"),
    "release_contexts": ("_task_context", "release_many"),
    "type_names": ("_ops", "type_names"),
}

# Names are declared for static tooling but acquire values only through the
# module's PEP 562 resolver.
atom_added: _Any
atom_removed: _Any
async_cancel: _Any
async_discard: _Any
async_prepare: _Any
async_start: _Any
capture_context: _Any
capture_contexts: _Any
construct_token: _Any
dispatch: _Any
dispatch_context: _Any
dispatch_inverse: _Any
dispatch_inverse_context: _Any
dispatch_inverse_raw: _Any
dispatch_inverse_raw_context: _Any
dispatch_many: _Any
dispatch_many_context: _Any
dispatch_raw: _Any
dispatch_raw_context: _Any
dispatch_raw_many: _Any
dispatch_raw_many_context: _Any
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
fork_context: _Any
fork_contexts: _Any
is_matchable: _Any
match_object: _Any
path_begin: _Any
path_step: _Any
path_value: _Any
release_context: _Any
release_contexts: _Any
type_names: _Any

__all__ = [
    "async_cancel",
    "async_discard",
    "async_prepare",
    "async_start",
    "atom_added",
    "atom_removed",
    "capture_context",
    "capture_contexts",
    "construct_token",
    "dispatch",
    "dispatch_context",
    "dispatch_inverse",
    "dispatch_inverse_context",
    "dispatch_inverse_raw",
    "dispatch_inverse_raw_context",
    "dispatch_many",
    "dispatch_many_context",
    "dispatch_raw",
    "dispatch_raw_context",
    "dispatch_raw_many",
    "dispatch_raw_many_context",
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
    "fork_context",
    "fork_contexts",
    "is_matchable",
    "match_object",
    "path_begin",
    "path_step",
    "path_value",
    "release_context",
    "release_contexts",
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
