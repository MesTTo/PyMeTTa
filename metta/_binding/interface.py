"""Purpose: declare the Python binding's imported and exported services.

Guarantees: bindinggen checks every crossing against these rows and the
implementation's signature; native imports must have an engine service row
[tested: test_binding_crossing_mutations_refuse; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
The value and foreign-space length services are declared with their generated
ownership providers [tested: python extensions/python/tools/bindinggen.py;
commit=d336b911f0d727b50a5660eb86f5ed44b35303b5].
Decides: dynamic object calls are capabilities of named predicates. A capability
does not admit undeclared static callbacks or crossings in another predicate.
"""

from __future__ import annotations

from typing import NamedTuple

# A renamed export records both spellings; an unchanged export records one.
Export = str | tuple[str, str]

# closed-set: decides; policy=host callbacks exported through metta_ops; reads=none
CALLBACK_GROUPS: dict[str, tuple[Export, ...]] = {
    "metta.aio._ops": (
        ("async_cancel", "cancel"), ("async_discard", "discard"),
        ("async_prepare", "prepare"), ("async_start", "start"),
    ),
    "metta.events": ("atom_added", "atom_removed", "segment_committed"),
    "metta._binding.task_context": (
        ("capture_context", "snapshot"), ("capture_contexts", "snapshot_many"),
        ("fork_context", "fork"), ("fork_contexts", "fork_many"),
        ("release_context", "release"), ("release_contexts", "release_many"),
    ),
    "metta._binding.tokens": ("construct_token",),
    "metta._spaces.handle": ("drop_completed",),
    "metta._spaces.scope": ("transaction_body",),
    "metta._spaces.lease": (("lease_aborted", "aborted"), ("space_released", "released")),
    "metta._binding.dispatch": ("dispatch", "type_names"),
    "metta._binding.runtime": ("engine_message", "heartbeat_tick"),
    "metta.foreign": (
        "foreign_add", "foreign_add_many", "foreign_add_token", "foreign_atoms",
        "foreign_tokens", "foreign_clear", "foreign_match", "foreign_plan",
        "foreign_pushdown", "foreign_refuse", "foreign_remove",
        "foreign_remove_token", "foreign_participant", "is_matchable",
        "match_object",
    ),
    "metta.paths": (
        ("path_begin", "_path_begin"), ("path_step", "_path_step"),
        ("path_value", "_path_value"),
    ),
    "metta._errors.errors": ("stream_reraise",),
}

# Direct imports retain their defining namespace. Their signatures are read
# from source, so changing a provider also checks its binding consumers.
# closed-set: decides; policy=direct Python services the binding may import; reads=none
PYTHON_SERVICES = {
    "metta._binding.host": (
        "algebra_equal", "apply", "build_dict", "build_list", "build_tuple",
        "class_names", "declare_type", "declared_type_texts", "dot", "evaluate",
        "evaluate_grounded", "grounded_apply", "is_callable", "is_numeric", "iterate",
        "iterate_once",
        "numeric_operation", "render", "resolve", "resolve_grounded",
        "sequence_length", "sized_length", "stream_reraise", "stream_tag", "unboxed",
    ),
    "metta._catalog.bounds": (
        "bound_row_changed", "bound_transaction_started", "bound_transaction_finished",
    ),
    "metta._errors.errors": ("is_transport_failure",),
    "metta.foreign": ("_provider_length",),
    "metta.algebra": ("_carrier_type_accepts",),
    "builtins": ("id", "str", "type"),
    "importlib.util": ("module_from_spec", "spec_from_file_location"),
    "sys": (
        "modules.__contains__", "modules.__setitem__", "modules.pop",
        "path.clear", "path.copy", "path.extend", "path.insert",
    ),
}

# CPython does not publish inspect.signature for these C callables. These are
# the positional shapes used here, held by executable crossing tests.
# [tested: test_binding_standard_library_services; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
C_SIGNATURES = {"builtins:str": (0, 1, 2, 3), "builtins:type": (1, 3), "sys:modules.pop": (1, 2)}

# Each target's arity and audience come from engine/ext_points.pl:kind/2.
# closed-set: decides; policy=Python aliases of engine services; reads=engine/ext_points.pl:kind/2
NATIVE_FORWARDS = {
    "metta_py_cursor_chunk": "metta_host_hold_chunk/3",
    "metta_py_cursor_close": "metta_host_hold_close/1",
    "metta_control_signal_line": "metta_host_control_signal_line/2",
    "metta_py_space_capability_error": "metta_host_space_capability_error/4",
    "metta_py_function_generation": "metta_host_function_generation/1",
    "metta_py_clear": "metta_host_clear_space/1",
    "metta_py_fast_load": "metta_host_load_fast/2",
    "metta_py_unregister_token": "metta_host_unregister_reader_token/1",  # nosec B105 # reader-token predicate indicator
    "metta_py_module": "space_module/2",
    "metta_py_in_module": "with_metta_module/2",
}

# Each entry retains the source audience of its supplied clauses. Included
# files inherit their caller's module; use_module files declare their own.
LOAD_ENTRIES = {"engine": "surface.pl", "host": "shim.pl"}

# The first measured width with separated CPU ranges. Shared projection scans
# the name list per column; indexed projection resolves each name once.
# [measured 2026-09-09: 64 names, shared 0.101544s and indexed 0.080958s minimum;
# command=python extensions/python/benchmarks/probes/query_projection.py --repeats 1000 --samples 11;
# fixture=one native fact at 2, 16, 64 and 128 names; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
QUERY_INDEX_CROSSOVER = 64


class Capability(NamedTuple):
    """A dynamic receiver or member permitted at one source predicate."""

    owner: str
    module: str | None
    member: str | None
    arity: int | None
    reason: str


# closed-set: decides; policy=object-call capabilities at the native boundary; reads=none
CAPABILITIES = (
    Capability("metta_py_capture_participant/3", None, "__call__", 0,
               "Retain the selected provider's bound transaction operations for completion."),
    Capability("metta_py_call/3", "metta._binding.host", None, None,
               "Apply a declared host service; bindinggen also checks source callers."),
    Capability("py-call/3", None, None, None,
               "The language's explicit Python call selects its receiver and arguments."),
    Capability("py-call/3", "builtins", None, None,
               "The language's explicit Python call may select a builtin."),
    Capability("load_python_module/5", None, "loader.exec_module", 1,
               "Execute the module spec created by importlib.util."),
    Capability("metta_py_saga_transaction/4", None, "__call__", 0,
               "Run, commit or roll back the retained saga transaction."),
    Capability("metta_py_saga_eval_all/5", None, "__call__", 1,
               "Journal an evaluated saga answer before returning it."),
    Capability("metta_py_saga_wrapped_call/4", None, "__call__", 1,
               "Journal a wrapped operation's receipt."),
)


def callbacks() -> dict[str, tuple[str, str]]:
    """Project the lazy facade's aliases without importing any implementation."""
    return {
        (export if isinstance(export, str) else export[0]):
        (module, export if isinstance(export, str) else export[1])
        for module, exports in CALLBACK_GROUPS.items() for export in exports
    }
