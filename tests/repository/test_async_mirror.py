"""Purpose: prove generated faces preserve door contracts and reject edits.

Guarantees: generated signatures, overloads and docs agree with synchronous
doors; handwritten worker parameters follow their declared divergence
[tested: this file; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Owns resources: mutation witnesses use temporary source or scoped reads and
leave the checked-in projections unchanged.
"""

from __future__ import annotations

import ast
import builtins
import copy
import sys
from pathlib import Path

import pytest

from metta.doors import Owner, Tier

REPO = Path(__file__).resolve().parents[4]
CORE = REPO / "extensions/python/metta"
WORKER = CORE / "aio/_worker.py"
MIRROR = CORE / "aio/_mirror.py"
SPACE = CORE / "_faces/space.py"
INIT = CORE / "__init__.py"
sys.path.insert(0, str(REPO / "extensions/python/tools"))

import aiogen  # noqa: E402 -- test the build command
import doorgen  # noqa: E402 -- read body declarations independently of emission
from aio_divergences import DIVERGENT, EXCLUDED, MODULE_DOORS, PRIVATE_TARGET  # noqa: E402


def _methods(path, name):
    tree = ast.parse(path.read_text())
    scope = tree.body if name is None else next(node.body for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    return {node.name: node for node in scope if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not any(ast.unparse(mark).endswith("overload") for mark in node.decorator_list)}


def _sources():
    sources = {}
    for owner, modules in (
        ("MeTTa", ((CORE / "_spaces/context.py", "MeTTaBase"), (CORE / "_faces/metta.py", "MeTTa"))),
        ("Space", ((CORE / "_spaces/handle.py", "SpaceHandle"), (SPACE, "Space"))),
    ):
        for path, name in modules:
            sources.update({key: (owner, node, path) for key, node in _methods(path, name).items()})
    for row in doorgen.all_rows():
        if Tier.async_ in row.tiers and (
            row.owner is Owner.namespace or (row.owner is Owner.space and Tier.sync not in row.tiers)
        ):
            nodes, _ = doorgen.body_nodes(row)
            target = row.alias or row.python if row.owner is Owner.namespace else PRIVATE_TARGET.get(row.python, row.python)
            sources[target] = (row.body.reference, nodes[-1], doorgen.module_path(row.body.module))
    return sources


def _parameter_shape(node):
    """Retain parameter kinds and both variadics while dropping the receiver."""
    args = copy.deepcopy(node.args)
    (args.posonlyargs or args.args).pop(0)
    return ([p.arg for p in args.posonlyargs], [p.arg for p in args.args],
            sorted(p.arg for p in args.kwonlyargs),
            args.vararg.arg if args.vararg else None, args.kwarg.arg if args.kwarg else None)


def _resolved(node, source):
    """Compare annotations and defaults after resolving their import aliases."""
    imports = {}
    tree = ast.parse(source.read_text())
    module = (
        ".".join(source.relative_to(CORE.parent).with_suffix("").parts).removesuffix(".__init__")
        if CORE in source.parents else source.stem
    )
    for statement in tree.body:
        if isinstance(statement, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            imports[statement.name] = module + "." + statement.name
    for statement in ast.walk(tree):
        if isinstance(statement, ast.Import):
            imports.update({name.asname or name.name.partition(".")[0]: name.name if name.asname else name.name.partition(".")[0] for name in statement.names})
        elif isinstance(statement, ast.ImportFrom):
            imports.update({name.asname or name.name: statement.module + "." + name.name for name in statement.names if statement.module})

    class Names(ast.NodeTransformer):
        def visit_Name(self, item):
            name = imports.get(item.id, "builtins." + item.id if item.id in vars(builtins) else item.id)
            return ast.Name(id=name, ctx=ast.Load())

        def visit_Attribute(self, item):
            resolved = self.generic_visit(item)
            spelling = ast.unparse(resolved)
            prefix = module + "."
            if spelling.startswith(prefix):
                name, separator, rest = spelling.removeprefix(prefix).partition(".")
                if name in imports:
                    return ast.Name(id=imports[name] + (separator + rest if separator else ""), ctx=ast.Load())
            return resolved

    return ast.unparse(Names().visit(copy.deepcopy(node))) if node is not None else None


def _signature(node, source, *, receiver=True):
    args = copy.deepcopy(node.args)
    if receiver:
        (args.posonlyargs or args.args).pop(0)
    return _resolved(args, source), _resolved(node.returns, source)


def test_the_async_mirror_is_generated_from_the_sync_surface():
    """Check all four projections against the declaration reader."""
    assert aiogen.main([]) == 0


def test_every_generated_door_is_spaces_door():
    """Ordinary worker doors retain the complete signature and exact docs."""
    generated, sources = _methods(MIRROR, "AsyncMeTTa"), _sources()
    assert len(generated) >= 60
    for name, node in generated.items():
        target = PRIVATE_TARGET.get(name, name)
        assert target in sources, name
        _, original, path = sources[target]
        assert ast.get_docstring(node) == ast.get_docstring(original), name
        if name not in DIVERGENT:
            assert _signature(node, MIRROR) == _signature(original, path), name


def _async_parameter_drifts():
    sources = _sources()
    methods = {**_methods(WORKER, "AsyncMeTTaBase"), **_methods(MIRROR, "AsyncMeTTa")}
    drifts = []
    for name, node in sorted(methods.items()):
        target = PRIVATE_TARGET.get(name, name)
        if name.startswith("_") or target not in sources:
            continue
        owner, reference, _ = sources[target]
        expected_from = f"{owner}.{target}"
        if name in DIVERGENT:
            parameters, reason = DIVERGENT[name]
            assert len(reason.split()) >= 8, name
            reference = ast.parse(f"def replacement({parameters}): pass").body[0]
            expected_from = f"DIVERGENT[{name!r}]"
        expected, actual = _parameter_shape(reference), _parameter_shape(node)
        if expected != actual:
            drifts.append(f"DRIFT {name}: {expected_from} {expected!r}; AsyncMeTTa {actual!r}")
    return drifts


def test_every_async_counterpart_has_the_sync_parameters():
    """A handwritten worker method is checked against the same sync sources."""
    assert not (drifts := _async_parameter_drifts()), "\n".join(drifts)


def test_the_parameter_gate_catches_a_missing_handwritten_parameter(tmp_path, monkeypatch):
    """Removing the worker's journal keyword must fail the actual parity check."""
    original = WORKER.read_text()
    node = _methods(WORKER, "AsyncMeTTaBase")["space"]
    parameter = next(p for p in node.args.kwonlyargs if p.arg == "journal")
    lines = original.splitlines(keepends=True)
    del lines[parameter.lineno - 1]
    copied = tmp_path / "worker.py"
    copied.write_text("".join(lines))
    monkeypatch.setattr(sys.modules[__name__], "WORKER", copied)
    with pytest.raises(AssertionError, match=r"DRIFT space: MeTTa\.space"):
        test_every_async_counterpart_has_the_sync_parameters()
    copied.write_text(original)
    test_every_async_counterpart_has_the_sync_parameters()


def test_the_parameter_gate_requires_the_subscribe_divergence(monkeypatch):
    """Removing the callback-to-stream ruling exposes the different parameters."""
    with monkeypatch.context() as patch:
        patch.delitem(DIVERGENT, "subscribe")
        with pytest.raises(AssertionError, match=r"DRIFT subscribe: Space\.subscribe"):
            test_every_async_counterpart_has_the_sync_parameters()
    test_every_async_counterpart_has_the_sync_parameters()


def test_the_async_mirror_gate_catches_a_planted_edit(monkeypatch):
    """A changed generated body makes the build command fail and restores cleanly."""
    original = MIRROR.read_text()
    read = Path.read_text
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", lambda path, *a, **kw: original + "\n# planted mirror drift\n" if path == MIRROR else read(path, *a, **kw))
        assert aiogen.main([]) == 1
    assert aiogen.main([]) == 0


def test_every_exclusion_names_a_live_door_and_a_reason():
    """Each exclusion and divergence still refers to an implemented operation."""
    sources = _sources()
    for name, reason in EXCLUDED.items():
        assert name in sources, name
        assert len(reason.split()) >= 6, name
    for name, (parameters, reason) in DIVERGENT.items():
        assert PRIVATE_TARGET.get(name, name) in sources, name
        assert parameters.startswith("self"), name
        assert len(reason.split()) >= 8, name


def test_the_module_tier_is_generated_from_the_sync_surface():
    """Root forwarders preserve every argument, return annotation and body doc."""
    text = INIT.read_text().split("# begin generated module tier\n", 1)[1].split("# end generated module tier", 1)[0]
    methods = {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)
               and not any(ast.unparse(mark).endswith("overload") for mark in node.decorator_list)}
    assert set(methods) == {name for name, _ in MODULE_DOORS}
    sources = _sources()
    for name, target in MODULE_DOORS:
        node = methods[name]
        _, original, path = sources[target]
        assert _signature(node, INIT, receiver=False) == _signature(original, path), name
        assert ast.get_docstring(node) == ast.get_docstring(original) + "\n\nRuns against the default context's self space.", name
