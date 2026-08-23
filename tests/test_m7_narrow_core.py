"""Purpose: prove the Fork 4 surface collapse deletes superseded doors.
Guarantees:
  - the renamed package surface has 88 names and keeps ``record`` and
    ``order_key`` absent [tested: test_m7_narrow_core_surface;
    commit=b2527d32dc851615e6cf1e11c94ac017d4e78c86]
  - the published before/after counts are exact for ``MeTTa`` and ``metta``
    [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every retired root, context, and atom name is absent rather than aliased
    [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - all fifteen ``declare_*`` spellings are absent from both synchronous and
    asynchronous space handles [tested: test_m7_narrow_core_surface;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - plain import and ``dir(metta)`` load no satellite, while either explicit
    import order preserves real module identity [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the upstream ``python.petta`` alias and its two-method ``PeTTa`` wrapper
    are absent [tested: test_upstream_python_package_path_is_gone;
    commit=b2527d32dc851615e6cf1e11c94ac017d4e78c86]
Owns:
  - subprocesses used for clean import-order probes are waited synchronously
    by ``subprocess.run(check=True)`` [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Decides:
  - ``BASELINE_*`` and ``FINAL_*`` are the published surface metrics
    [measured: 90 to 20 MeTTa names and 152 to 88 metta names after the
    module-tier family and the package rename;
    command=python -m pytest bindings/python/tests/test_m7_narrow_core.py -q;
    fixture=a142938d baseline and the current generated root; commit=b2527d32dc851615e6cf1e11c94ac017d4e78c86]
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

import metta
from metta import MeTTa, Space
from metta import atoms as atom_module

BASELINE_METTA_METHODS = 90
BASELINE_PACKAGE_EXPORTS = 152
FINAL_METTA_METHODS = 20
# 61 at the narrow-core commit; +4 when the R6 merge promoted the canonical
# atoms TRUE, FALSE and UNIT to root values; +1 when
# R1 exported the static fn namespace at the root; +8 when R5 landed its
# ruled doors (typed, arrow, the keyword builders, State and solve's kin),
# followed by the five newly surfaced module-tier verbs (trace replaces its
# satellite module at the same name, so it does not change the count).
FINAL_METTA_EXPORTS = 88

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
    "HERE",
    "PeTTa",
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
    "functools",
    "importlib",
    "is_ground",
    "logging",
    "map_atoms",
    "pretty",
    "query",
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
    # Importable implementation modules are not package attributes. ``define``
    # is now the ruled default-engine verb, not the implementation module.
    "answer",
    "atoms",
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

REMOVED_DECLARATION_CEREMONY = {
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
    from metta.aio import AsyncMeTTa

    assert len(_public_names(MeTTa)) == FINAL_METTA_METHODS
    assert len(_public_names(metta)) == FINAL_METTA_EXPORTS
    assert BASELINE_METTA_METHODS > FINAL_METTA_METHODS
    assert BASELINE_PACKAGE_EXPORTS > FINAL_METTA_EXPORTS
    assert metta.__dir__() == sorted(metta.__all__)
    _assert_absent(MeTTa, REMOVED_FROM_METTA)
    _assert_absent(metta, REMOVED_FROM_ROOT)
    assert "janus" not in dir(metta)
    assert "janus" not in metta.__all__
    assert "janus" not in vars(metta)
    _assert_absent(atom_module, REMOVED_FROM_ATOMS)
    _assert_absent(AsyncMeTTa, REMOVED_FROM_ASYNC)
    _assert_absent(Space, REMOVED_DECLARATION_CEREMONY)
    _assert_absent(AsyncMeTTa, REMOVED_DECLARATION_CEREMONY)


def test_m7_satellites_are_lazy_and_identity_stable():
    """Check laziness and both real-module identity orders in fresh processes."""
    root = Path(__file__).resolve().parents[3]
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    names = repr(sorted(SATELLITES))
    scripts = [
        f"""
import importlib
import sys
import metta
names = {names}
assert all(f'metta.{{name}}' not in sys.modules for name in names)
dir(metta)
assert all(f'metta.{{name}}' not in sys.modules for name in names)
for name in names:
    first = getattr(metta, name)
    assert first is importlib.import_module(f'metta.{{name}}')
    assert getattr(metta, name) is first
""",
        f"""
import importlib
import metta
names = {names}
for name in names:
    first = importlib.import_module(f'metta.{{name}}')
    assert getattr(metta, name) is first
    assert importlib.import_module(f'metta.{{name}}') is first
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
    factory = metta.space
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("metta.space")
    assert metta.space is factory


def test_m7_unknown_attribute_has_normal_module_error():
    """PEP 562 preserves Python's normal unknown-attribute diagnostic."""
    name = "misspelled"
    with pytest.raises(AttributeError) as raised:
        getattr(metta, name)
    assert str(raised.value) == "module 'metta' has no attribute 'misspelled'"


def test_upstream_python_package_path_is_gone():
    """The old package alias and source-string wrapper have no import path."""
    root = Path(__file__).resolve().parents[3]
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import metta

assert 'PeTTa' not in metta.__all__
assert 'HERE' not in metta.__all__
assert 'query' not in metta.__all__
assert not hasattr(metta, 'PeTTa')
assert not hasattr(metta, 'HERE')
assert not hasattr(metta, 'query')
try:
    __import__('python.petta')
except ModuleNotFoundError:
    pass
else:
    raise AssertionError('python.petta still imports')
""",
        ],
        cwd=root,
        env=environment,
        check=True,
    )
