"""Purpose: prove the Fork 4 surface collapse deletes superseded doors.
Guarantees:
  - the post-R5 narrow package surface has 69 names and keeps ``record`` and
    ``order_key`` absent [tested: test_m7_narrow_core_surface;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - the published before/after counts are exact for ``MeTTa`` and ``petta``
    [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every retired root, context, and atom name is absent rather than aliased
    [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - plain import and ``dir(petta)`` load no satellite, while either explicit
    import order preserves real module identity [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the retained upstream package path resolves to the canonical module and
    keeps the original two-method ``PeTTa`` wrapper [tested:
    test_upstream_python_package_path_is_canonical; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Owns:
  - subprocesses used for clean import-order probes are waited synchronously
    by ``subprocess.run(check=True)`` [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Decides:
  - ``BASELINE_*`` and ``FINAL_*`` are the published M7 surface metrics
    [measured: 90 to 20 MeTTa names and 152 to 69 petta names after R5;
    command=python -m pytest bindings/python/tests/test_m7_narrow_core.py -q;
    fixture=a142938d baseline and cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5 final; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

import petta
from petta import MeTTa
from petta import atoms as atom_module

BASELINE_METTA_METHODS = 90
BASELINE_PETTA_EXPORTS = 152
FINAL_METTA_METHODS = 20
FINAL_PETTA_EXPORTS = 69

SATELLITES = {
    "aio",
    "algebra",
    "arrays",
    "casting",
    "convert",
    "derivation",
    "events",
    "foreign",
    "integrate",
    "lint",
    "manifest",
    "parallel",
    "paths",
    "remote",
    "spaces",
    "structures",
    "subscribe",
    "tables",
    "testing",
    "trace",
    "vocabularies",
    "wire",
}

REMOVED_FROM_METTA = {
    "add",
    "add_table",
    "add_tagged_fact",
    "add_tagged_rule",
    "arities",
    "assuming",
    "atoms",
    "batch",
    "builtins",
    "cache",
    "cast",
    "clear",
    "copy",
    "count",
    "declare_admits",
    "declare_agenda",
    "declare_algebra",
    "declare_annotations",
    "declare_capacity",
    "declare_context",
    "declare_emits",
    "declare_events",
    "declare_handles",
    "declare_image",
    "declare_merge",
    "declare_on_error",
    "declare_reaction",
    "declare_source",
    "declare_writes",
    "derivation",
    "digest",
    "disassemble",
    "drop",
    "eval",
    "eval_status",
    "evaluate_algebra",
    "events",
    "first",
    "fn",
    "hyperpose",
    "integrate",
    "is_function",
    "is_function_here",
    "lint",
    "load",
    "new_space",
    "one",
    "parallel",
    "parse",
    "pool",
    "prepare",
    "profile",
    "profile_extension",
    "query",
    "register_op",
    "register_space",
    "register_token",
    "remove",
    "run",
    "run_status",
    "sample_rates",
    "save",
    "space_name",
    "space_names",
    "stream",
    "subscribe",
    "transactional",
    "type",
    "unregister",
    "unregister_space",
    "unregister_token",
    "why",
}

REMOVED_FROM_ROOT = {
    "DECLINE",
    "Decline",
    "Expr",
    "Gnd",
    "MettaName",
    "REFLECTION_SPACE",
    "SpaceName",
    "Sym",
    "Var",
    "alpha_eq",
    "atom_from_wire",
    "backend_info",
    "bridge",
    "cast",
    "decode",
    "default_engine",
    "encode",
    "expr",
    "fn",
    "functools",
    "importlib",
    "is_ground",
    "logging",
    "map_atoms",
    "pretty",
    "record",
    "register_object_repr_protocol",
    "sym",
    "sys",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
    # Specialist objects no longer re-exported from the root.
    "AlgebraDeclarationError",
    "AlgebraEvaluation",
    "AlgebraEvaluationError",
    "AlgebraLawError",
    "AlgebraOperationError",
    "AlgebraRequirementError",
    "Amplitude",
    "DeclaredAlgebra",
    "LinearEvidenceError",
    "PlanDecision",
    "RateDeclarationError",
    "TaggedAnswer",
    "tagged_fact",
    "tagged_rule",
    "AssertionFailure",
    "CompileError",
    "EngineError",
    "InferenceLimitError",
    "Interrupted",
    "MettaOperationError",
    "MettaResultError",
    "MettaSyntaxError",
    "ResourceLimitError",
    "SourceNotFound",
    "SpaceCapabilityError",
    "StrictError",
    "SubscriberError",
    "TimeLimitError",
    "Adder",
    "Clearer",
    "CustomMatch",
    "Enumerable",
    "Matcher",
    "Remover",
    "Event",
    "EventStream",
    "Fold",
    "Subscription",
    "Builtin",
    "Derivation",
    "Fact",
    "Step",
    "Truncated",
    "Attr",
    "Key",
    "Path",
    "path",
    "DefinitionFacts",
    "SourceSpan",
    "CastError",
    "Boot",
    "SaveFormat",
    "engine_thread",
    "OPERATOR_LOWERINGS",
    "OperatorLowering",
    "order_key",
    "register_object_repr",
    "unregister_object_repr",
    "Row",
    "Rows",
    "Cursor",
    "EngineProfile",
    "Prepared",
    # Importable implementation modules are not package attributes.
    "answer",
    "atoms",
    "define",
    "errors",
    "ops",
    "results",
    "persistent",
    "das",
}

REMOVED_FROM_ATOMS = {
    "DECLINE",
    "Decline",
    "Expr",
    "Gnd",
    "Sym",
    "Var",
    "alpha_eq",
    "atom_from_wire",
    "decode",
    "encode",
    "expr",
    "is_ground",
    "map_atoms",
    "pretty",
    "register_object_repr_protocol",
    "sym",
    "unregister_object_repr_protocol",
    "val",
    "var",
    "variables",
}

REMOVED_FROM_ASYNC = {
    "disassemble",
    "new_space",
    "register_op",
    "register_space",
    "unregister",
    "unregister_space",
}


def _public_names(value) -> set[str]:
    return {name for name in dir(value) if not name.startswith("_")}


def _assert_absent(value, names: set[str]) -> None:
    namespace = vars(value)
    listed = set(dir(value))
    for name in names:
        assert name not in listed
        assert name not in namespace
        with pytest.raises(AttributeError):
            getattr(value, name)


def test_m7_narrow_core_surface():
    """Publish the M7 metric and prove every superseded name is gone."""
    from petta.aio import AsyncMeTTa

    assert len(_public_names(MeTTa)) == FINAL_METTA_METHODS
    assert len(_public_names(petta)) == FINAL_PETTA_EXPORTS
    assert BASELINE_METTA_METHODS > FINAL_METTA_METHODS
    assert BASELINE_PETTA_EXPORTS > FINAL_PETTA_EXPORTS
    assert petta.__dir__() == sorted(petta.__all__)
    _assert_absent(MeTTa, REMOVED_FROM_METTA)
    _assert_absent(petta, REMOVED_FROM_ROOT)
    assert "janus" not in dir(petta)
    assert "janus" not in petta.__all__
    assert "janus" in vars(petta)  # retained only for upstream python.petta
    _assert_absent(atom_module, REMOVED_FROM_ATOMS)
    _assert_absent(AsyncMeTTa, REMOVED_FROM_ASYNC)


def test_m7_satellites_are_lazy_and_identity_stable():
    """Check laziness and both real-module identity orders in fresh processes."""
    root = Path(__file__).resolve().parents[3]
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    names = repr(sorted(SATELLITES))
    scripts = [
        f"""
import importlib
import sys
import petta
names = {names}
assert all(f'petta.{{name}}' not in sys.modules for name in names)
dir(petta)
assert all(f'petta.{{name}}' not in sys.modules for name in names)
for name in names:
    first = getattr(petta, name)
    assert first is importlib.import_module(f'petta.{{name}}')
    assert getattr(petta, name) is first
""",
        f"""
import importlib
import petta
names = {names}
for name in names:
    first = importlib.import_module(f'petta.{{name}}')
    assert getattr(petta, name) is first
    assert importlib.import_module(f'petta.{{name}}') is first
""",
    ]
    for script in scripts:
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=environment,
            check=True,
        )


def test_m7_space_factory_keeps_identity():
    """No physical submodule can overwrite the callable space factory."""
    factory = petta.space
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("petta.space")
    assert petta.space is factory


def test_m7_unknown_attribute_has_normal_module_error():
    """PEP 562 preserves Python's normal unknown-attribute diagnostic."""
    name = "misspelled"
    with pytest.raises(AttributeError) as raised:
        getattr(petta, name)
    assert str(raised.value) == "module 'petta' has no attribute 'misspelled'"


def test_upstream_python_package_path_is_canonical():
    """Retain only upstream's package path, wrapper methods, and CLI module."""
    root = Path(__file__).resolve().parents[3]
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import importlib
import petta

upstream = importlib.import_module('python.petta')
assert upstream is petta
assert upstream.PeTTa is petta.PeTTa
assert {
    name for name in dir(upstream.PeTTa) if not name.startswith('_')
} == {'load_metta_file', 'process_metta_string'}
assert callable(importlib.import_module('python.petta.cli').main)
""",
        ],
        cwd=root,
        env=environment,
        check=True,
    )
