"""Purpose: generate host surfaces from the typed Python door contracts.

Assumes: implementations remain in the modules their rows name.
Guarantees: changed membership, signatures, sugar points, or evidence cannot
  leave a stale projection unnoticed [tested:
  test_every_door_projection_is_current,
  test_door_sync_detects_a_planted_change_in_each_projection; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
Decides: rows choose the surface. Source syntax checks a hand implementation
  against its row and supplies no independent membership list.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import copy
import inspect
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import is_dataclass, replace
from enum import Enum
from functools import lru_cache
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
SEAT = ROOT / "extensions/python"
CORE = SEAT / "metta"
sys.path[:0] = [str(SEAT), str(TOOLS)]

from reference import quote, split_top_level  # noqa: E402

from metta import doors, vocabularies  # noqa: E402  -- the engine-free row grammar
from metta._refusals import REFUSALS  # noqa: E402
from metta.doors import Door, Owner, Signature, Tier  # noqa: E402

START = "    # begin generated doors: "
END = "    # end generated doors: "
SCHEMA_START = "# begin generated remote operations"
SCHEMA_END = "# end generated remote operations"
SHEET_START = "<!-- begin generated door contracts -->"
SHEET_END = "<!-- end generated door contracts -->"


def module_path(name: str, root: Path = ROOT) -> Path:
    """Locate a core or workspace module without importing it."""
    seat = root / "extensions/python"
    if name.startswith("metta."):
        path = seat / (name.replace(".", "/") + ".py")
        if path.is_file():
            return path
    found = [path for path in (seat / "ext").glob("metta-*/*.py") if path.stem == name]
    if len(found) != 1:
        msg = f"door implementation module {name!r} has {len(found)} source files"
        raise ValueError(msg)
    return found[0]


def package_rows(root: Path = ROOT) -> tuple[Door, ...]:
    """Read literal DOORS declarations without executing package imports."""
    scope = {name: value for name, value in vars(doors).items()
             if isinstance(value, type) and (is_dataclass(value) or issubclass(value, Enum))}
    result: list[Door] = []
    for path in sorted((root / "extensions/python/ext").glob("metta-*/*.py")):
        stat = path.stat()
        _, tree = _source(path, stat.st_mtime_ns, stat.st_size)
        for node in tree.body:
            if ((isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "DOORS")
                    or (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "DOORS" for target in node.targets))):
                expression = node.value
            else:
                continue
            if expression is None:
                msg = f"{path}: DOORS has no records"
                raise ValueError(msg)
            for item in ast.walk(expression):
                if isinstance(item, ast.Call) and (
                    not isinstance(item.func, ast.Name) or item.func.id not in scope
                ):
                    msg = f"{path}: door metadata calls outside the row grammar"
                    raise ValueError(msg)
                if isinstance(item, ast.Attribute) and (
                    not isinstance(item.value, ast.Name) or item.value.id not in scope
                    or not issubclass(scope[item.value.id], Enum) or item.attr.startswith('_')
                ):
                    msg = f"{path}: door metadata reads outside the row grammar"
                    raise ValueError(msg)
                if not isinstance(item, (ast.Tuple, ast.List, ast.Constant, ast.Call, ast.Name,
                                         ast.Load, ast.Attribute, ast.keyword)):
                    msg = f"{path}: DOORS must contain literal records"
                    raise TypeError(msg)
            value = eval(compile(ast.Expression(expression), str(path), "eval"), {"__builtins__": {}, **scope})  # noqa: S307  -- constructors are checked above; no package code executes
            if not isinstance(value, tuple) or any(not isinstance(row, Door) for row in value):
                msg = f"{path}: DOORS must be a tuple of Door records"
                raise TypeError(msg)
            result.extend(value)
    return tuple(result)


def all_rows(root: Path = ROOT) -> tuple[Door, ...]:
    """The declared core and every workspace contributor."""
    return doors.validate((*doors.DOORS, *package_rows(root)))


def _canonical(text: str | None) -> str | None:
    if text is None:
        return None
    return ast.unparse(ast.parse(text, mode="eval").body)


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Signature:
    return Signature(
        ast.unparse(node.args), ast.unparse(node.returns) if node.returns else None,
        ", ".join(ast.unparse(param) for param in node.type_params),
        tuple(ast.unparse(decorator) for decorator in node.decorator_list),
    )


def _same_signature(left: Signature, right: Signature, *, receiver: bool = False) -> bool:
    a, b = ast.parse(f"def door({left.parameters}): ...").body[0], ast.parse(f"def door({right.parameters}): ...").body[0]
    if receiver:
        for node in (a, b):
            first = [*node.args.posonlyargs, *node.args.args]
            if first:
                first[0].arg = "receiver"
    return (
        ast.dump(a.args, include_attributes=False) == ast.dump(b.args, include_attributes=False)
        and _canonical(left.returns) == _canonical(right.returns)
        and left.type_parameters == right.type_parameters
        and left.declarations == right.declarations
    )


def body_nodes(row: Door, root: Path = ROOT) -> tuple[list[ast.FunctionDef | ast.AsyncFunctionDef], str]:
    """Read the implementation a row names, without importing its module."""
    if row.body is None:
        return [], ""
    path = module_path(row.body.module, root)
    stat = path.stat()
    text, tree = _source(path, stat.st_mtime_ns, stat.st_size)
    held: list[ast.stmt] = tree.body
    parts = row.body.symbol.split(".")
    for part in parts[:-1]:
        cls = next((node for node in held if isinstance(node, ast.ClassDef) and node.name == part), None)
        if cls is None:
            msg = f"{row.key}: implementation class {part!r} is absent from {path}"
            raise ValueError(msg)
        held = cls.body
    nodes = [node for node in held if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == parts[-1]]
    declared_slot = row.inherited and any(
        isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id == parts[-1] for node in held
    )
    if not nodes and not declared_slot:
        msg = f"{row.key}: implementation {row.body.reference!r} is absent"
        raise ValueError(msg)
    return nodes, text


@lru_cache(maxsize=128)
def _source(path: Path, _modified: int, _size: int) -> tuple[str, ast.Module]:
    """Parse a source snapshot once across all contracts that name it."""
    text = path.read_text(encoding="utf-8")
    return text, ast.parse(text, filename=str(path))


def local_refusal_kinds(nodes: Iterable[ast.AST]) -> set[str]:
    """Read explicit local raises using the engine's own refusal class map."""
    classes = {row.cls: row.kind for row in REFUSALS.values()}
    found = set()
    for body in nodes:
        for node in ast.walk(body):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            call = node.exc
            name = ast.unparse(call.func)
            if name in classes:
                found.add(classes[name])
            elif name == "refuse" and call.args:
                kind = call.args[0]
                if isinstance(kind, ast.Constant) and isinstance(kind.value, str):
                    found.add(kind.value)
                elif isinstance(kind, ast.Attribute) and isinstance(kind.value, ast.Name) and kind.value.id == "RefusalKind":
                    found.add(str(getattr(doors.RefusalKind, kind.attr)))
    return found


def undeclared_members(rows: Iterable[Door], root: Path = ROOT) -> list[str]:
    """A public method added beside a generated class must become a row."""
    from aiogen import (  # noqa: PLC0415 -- that backend owns the context region
        METTA_END,
        METTA_START,
    )

    classes = {(row.body.module, row.body.symbol.rpartition('.')[0]) for row in rows
               if row.body and row.owner is not Owner.namespace and not row.inherited}
    found = []
    for module, name in sorted(classes):
        path = module_path(module, root)
        lines = path.read_text(encoding="utf-8").splitlines()
        regions = [(lines.index(START + name) + 1, lines.index(END + name) + 1)]
        if name == 'MeTTa':
            regions.append((lines.index(METTA_START) + 1, lines.index(METTA_END) + 1))
        tree = ast.parse('\n'.join(lines), filename=str(path))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
        for node in cls.body:
            if any(start <= node.lineno <= end for start, end in regions):
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_'):
                found.append(f"{module}:{name}.{node.name}: public implementation has no generated door declaration")
    return found


def contract_findings(rows: Iterable[Door] | None = None, root: Path = ROOT) -> list[str]:
    """Signature, evidence, and declared-refusal obligations of each row."""
    try:
        records = all_rows(root) if rows is None else doors.validate(rows)
    except (TypeError, ValueError, SyntaxError) as error:
        return [str(error)]
    found: list[str] = []
    targets: dict[Path, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for row in records:
        try:
            nodes, source = body_nodes(row, root)
        except ValueError as error:
            found.append(str(error))
            continue
        if nodes and len(nodes) != len(row.signatures):
            found.append(f"{row.key}: {len(row.signatures)} signatures describe {len(nodes)} implementation declarations")
        for expected, node in zip(row.signatures, nodes, strict=False):
            observed = _signature(node)
            if not _same_signature(expected, observed, receiver=row.owner is Owner.namespace):
                found.append(f"{row.key}: implementation signature differs from its row")
        if nodes:
            actual_doc = inspect.cleandoc(ast.get_docstring(nodes[-1], clean=False) or "")
            if actual_doc and actual_doc.strip() != row.docs.strip():
                found.append(f"{row.key}: implementation documentation differs from its row")
        for target in (*row.evidence, *(refusal.witness for refusal in row.refuses)):
            filename, separator, selector = target.partition("::")
            name = selector.partition('[')[0]
            path = root / filename
            if not separator or not name.startswith("test_") or not path.is_file():
                found.append(f"{row.key}: evidence {target!r} is not a repository test")
                continue
            if path not in targets:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                targets[path] = {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if name not in targets[path]:
                found.append(f"{row.key}: evidence test {target!r} does not exist")
        claimed = {refusal.kind for refusal in row.refuses}
        found.extend(f"{row.key}: local refusal {missing!r} has no declared witness"
                     for missing in sorted(local_refusal_kinds(nodes[-1:]) - claimed))
        for refusal in row.refuses:
            filename, _, selector = refusal.witness.partition('::')
            node = targets.get(root / filename, {}).get(selector.partition('[')[0])
            if node is None:
                continue
            expected = REFUSALS[refusal.kind].cls
            if not any(
                isinstance(call, ast.Call) and ast.unparse(call.func) == 'pytest.raises'
                and call.args and ast.unparse(call.args[0]) == expected
                for call in ast.walk(node)
            ):
                found.append(f"{row.key}: refusal {refusal.kind!r} witness must assert pytest.raises({expected})")
        if (row.binding and row.binding.door != "janus.prolog" and row.binding.door not in source
                and not any(row.binding.door in path.read_text(encoding="utf-8") for path in (root / "extensions/python/metta").glob("*.py"))):
            # Indirect engine bindings name a helper's crossing. The full
            # implementation module and its imported sibling carry that name.
            found.append(f"{row.key}: engine binding {row.binding.door!r} has no caller")
        # Access the structured fields here so this is the obligation reader,
        # including arguments whose types only exist in a host's own module.
        for arg in row.assumes.args:
            try:
                arg.type.to_atom()
            except (TypeError, SyntaxError) as error:
                found.append(f"{row.key}.{arg.name}: {error}")
        if row.fails_when.propagates is not True:
            found.append(f"{row.key}: an implementation failure must propagate")
    found.extend(undeclared_members(records, root))
    return found


def signature_lines(signature: Signature, name: str, indent: str = "    ") -> list[str]:
    """Render the exact row signature with normal line wrapping."""
    generics = f"[{signature.type_parameters}]" if signature.type_parameters else ""
    answer = f" -> {signature.returns}" if signature.returns else ""
    head = f"{indent}def {name}{generics}({signature.parameters}){answer}:"
    ignored = "  # type: ignore[" + ", ".join(signature.type_ignores) + "]" if signature.type_ignores else ""
    args = signature.node.args
    shadowed = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
                if arg.arg in vars(builtins)}
    shadow_note = "  # noqa: A002 -- the declared public parameter spelling"
    if len(head) <= 100:
        return [head + ignored + (shadow_note if shadowed else "")]
    return [
        f"{indent}def {name}{generics}(" + ignored,
        *(f"{indent}    {part.strip()}," + (shadow_note if part.strip().split(':')[0] in shadowed else "")
          for part in split_top_level(signature.parameters) if part.strip()),
        f"{indent}){answer}:",
    ]


def _doc_lines(doc: str, indent: str) -> list[str]:
    lines = doc.strip().splitlines()
    if not lines:
        return []
    escaped = [line.replace('\\', '\\\\').replace('"""', '\\"\\"\\"') for line in lines]
    exemptions = []
    # Match the first logical paragraph used by Ruff's punctuation check:
    # https://github.com/astral-sh/ruff/blob/0.16.1/crates/ruff_linter/src/rules/pydocstyle/helpers.rs#L15-L31
    summary = next((index for index, line in enumerate(lines)
                    if not line.strip() or set(line.strip()) <= set('-~=#')), len(lines))
    if lines[max(0, summary - 1)].rstrip()[-1] not in '.!?':
        exemptions.append('D415')
    if '\\' in doc:
        exemptions.append('D301')
    if len(escaped) == 1:
        note = f"  # noqa: {', '.join(exemptions)} -- preserve the declared documentation" if exemptions else ''
        return [f'{indent}"""{escaped[0]}"""{note}']
    end = '"""'
    if escaped[1].strip():
        exemptions.append('D205')
    if exemptions:
        end += f"  # noqa: {', '.join(exemptions)} -- preserve the declared documentation"
    return [f'{indent}"""{escaped[0]}', *(indent + line if line else "" for line in escaped[1:]), indent + end]


def _forward(signature: Signature) -> str:
    args = signature.node.args
    positional = [arg.arg for arg in (*args.posonlyargs, *args.args)][1:]
    if args.vararg:
        positional.append(f"*{args.vararg.arg}")
    positional.extend(f"{arg.arg}={arg.arg}" for arg in args.kwonlyargs)
    if args.kwarg:
        positional.append(f"**{args.kwarg.arg}")
    return ", ".join(positional)


def class_block(class_name: str, rows: Iterable[Door]) -> list[str]:
    """Static declarations and direct runtime bindings for one class."""
    rows = tuple(rows)
    selected = [row for row in rows if not row.inherited and row.body and row.body.symbol.rpartition('.')[0] == class_name and (Tier.sync in row.tiers or Tier.remote in row.tiers)]
    out = [START + class_name, "    # Generated from metta.doors by tools/doorgen.py.", "    if TYPE_CHECKING:"]
    for row in selected:
        for signature in row.signatures:
            out.extend("        @" + declaration for declaration in signature.declarations)
            out.extend(signature_lines(signature, row.python, "        "))
            if "overload" in signature.declarations:
                out[-1] = out[-1].replace(":  # type:", ": ...  # type:") if "# type:" in out[-1] else out[-1] + " ..."
                continue
            out.extend(_doc_lines(row.docs, "            "))
            name = row.body.symbol.rpartition('.')[2]
            implementation = f'cast("Any", self.{name})' if len(row.signatures) > 1 else f"self.{name}"
            expression = f"self.{name}" if row.is_property else f"{implementation}({_forward(signature)})"
            out.append(f"            return {expression}")
        out.append("")
    if class_name in {"Space", "MeTTa"}:
        tier = Tier.sync if class_name == "Space" else Tier.context
        names = sorted({row.provider.namespace for row in rows if row.owner is Owner.namespace and row.provider and tier in row.tiers})
        out.extend(f"        {name}: _door_namespaces.{_namespace_type(name, tier)}" for name in names)
        if names:
            out.append("")
    owner = Owner.rows if class_name == "Rows" else Owner.answers if class_name == "Answers" else None
    for row in rows:
        if row.owner is owner and row.body is None:
            for signature in row.signatures:
                out.extend(signature_lines(signature, row.python, "        "))
                out.extend(_doc_lines(row.docs, "            "))
                out.append("            ...")
            out.append("")
    out.append("    else:")
    for row in selected:
        name = row.body.symbol.rpartition('.')[2]
        note = "  # noqa: A003 -- bind the declared public door" if row.python in vars(builtins) else ""
        out.append(f"        {row.python} = {name}")
        out.append(f"        _bind_public({row.python}, {class_name!r}, {row.python!r}){note}")
    out.append(END + class_name)
    return out


def _namespace_type(name: str, tier: Tier) -> str:
    return ''.join(part.capitalize() for part in (*name.split('_'), tier.value))


class _QualifyAnnotation(ast.NodeTransformer):
    def __init__(self, module: str) -> None:
        self.module = module

    def visit_Name(self, item: ast.Name) -> ast.Name | ast.Attribute:
        """Keep builtins and qualify provider names in a protocol annotation."""
        if item.id in vars(builtins):
            return item
        return ast.Attribute(ast.Name(self.module, ast.Load()), item.id, ast.Load())


def namespace_types(rows: Iterable[Door]) -> str:
    """Static accessor protocols, with annotations scoped to their providers."""
    selected = [row for row in rows if row.owner is Owner.namespace and row.body]
    modules = {name: f"_body_{index}" for index, name in enumerate(sorted({row.body.module for row in selected}))}
    out = [
        '"""Purpose: type the accessor namespaces declared by installed workspace packages.',
        '', 'Generated by tools/doorgen.py from door rows.', '"""', '',
        'from __future__ import annotations', '', 'from typing import TYPE_CHECKING, Protocol', '',
        'if TYPE_CHECKING:',
    ]
    for local in (False, True):
        # Optional packages can be absent in a core-only typing environment.
        # The specific import guard preserves their types when installed:
        # https://github.com/python/mypy/blob/v2.3.0/docs/source/error_code_list2.rst#check-that-type-ignore-comment-is-used-unused-ignore
        guard = '' if local else '  # type: ignore[import-not-found, unused-ignore]'
        imports = [f'    import {name} as {alias}{guard}' for name, alias in modules.items()
                    if name.startswith('metta.') is local]
        if imports:
            out.extend([*imports, ''])
    accessors = sorted({(row.provider.namespace, tier) for row in selected for tier in row.tiers
                        if tier in {Tier.sync, Tier.context}})
    for name, tier in accessors:
        out.extend(['', f'class {_namespace_type(name, tier)}(Protocol):', f'    """The {tier.value} members of the {name} accessor."""', ''])
        for row in selected:
            if row.provider.namespace != name or tier not in row.tiers:
                continue
            for signature in row.signatures:
                node = copy.deepcopy(signature.node)
                args = node.args
                if row.body.receiver is not doors.Receiver.none:
                    (args.posonlyargs or args.args).pop(0)
                (args.posonlyargs or args.args).insert(0, ast.arg(arg='self'))
                # A protocol does not execute defaults. An annotation's
                # unqualified names retain the implementation module's scope.
                args.defaults = [ast.Constant(Ellipsis) for _ in args.defaults]
                args.kw_defaults = [None if value is None else ast.Constant(Ellipsis) for value in args.kw_defaults]
                qualifier = _QualifyAnnotation(modules[row.body.module])
                for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs, *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])):
                    if arg.annotation:
                        arg.annotation = qualifier.visit(arg.annotation)
                returns = ast.unparse(qualifier.visit(node.returns)) if node.returns else None
                projected = replace(signature, parameters=ast.unparse(args), returns=returns)
                for public in (row.python, '__call__') if row.provider.callable else (row.python,):
                    out.extend(signature_lines(projected, public))
                    out.extend(_doc_lines(row.docs, '        '))
                    out.append('        ...')
                    out.append('')
    return '\n'.join(out)


def declared_annotation_imports(path: Path) -> set[tuple[str, int]]:
    """Provider imports belong only to the exact generated annotation file."""
    if path != CORE / '_door_namespaces.py':
        return set()
    expected = namespace_types(all_rows())
    if path.read_text(encoding='utf-8') != expected:
        return set()
    tree = ast.parse(expected)
    return {(alias.name.partition('.')[0], node.lineno)
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names}


def replace_region(text: str, start: str, end: str, content: Iterable[str]) -> str:
    """Replace exactly one marked region, refusing missing or duplicate marks."""
    lines = text.splitlines()
    if lines.count(start) != 1 or lines.count(end) != 1:
        msg = f"expected exactly one {start!r} and {end!r}"
        raise ValueError(msg)
    first, last = lines.index(start), lines.index(end)
    if first >= last:
        msg = f"reversed generated region {start!r}"
        raise ValueError(msg)
    return '\n'.join([*lines[:first], *content, *lines[last + 1:]]) + '\n'


def class_projection(text: str, class_name: str, rows: Iterable[Door]) -> str:
    """The class projection; implementation functions stay outside its marks."""
    return replace_region(text, START + class_name, END + class_name, class_block(class_name, rows))


def virtual_class(owner: Owner) -> tuple[ast.ClassDef, list[str]]:
    """A row projection for the existing mirror and reference emitters."""
    selected = [row for row in all_rows() if row.owner is owner and not row.inherited]
    if owner is Owner.space:
        selected += [row for row in all_rows() if row.owner is Owner.namespace and row.alias and Tier.async_ in row.tiers]
    name = next(row.body.symbol.rpartition('.')[0] for row in selected if row.body and not row.inherited)
    lines = [f"class {name}:"]
    for row in selected:
        public = row.python
        if row.owner is Owner.namespace:
            public = row.alias or public
        elif Tier.sync not in row.tiers and Tier.async_ in row.tiers and row.body:
            public = row.body.symbol.rpartition('.')[2]
        for signature in row.signatures:
            projected_signature = signature
            if row.owner is Owner.namespace and row.body and row.body.receiver is not doors.Receiver.none:
                node = copy.deepcopy(signature.node)
                positional = [*node.args.posonlyargs, *node.args.args]
                positional[0].arg = "self"
                positional[0].annotation = None
                projected_signature = replace(signature, parameters=ast.unparse(node.args))
            lines.extend("    @" + declaration for declaration in projected_signature.declarations)
            lines.extend(signature_lines(projected_signature, public))
            if "overload" in projected_signature.declarations:
                lines[-1] = lines[-1].replace(":  # type:", ": ...  # type:") if "# type:" in lines[-1] else lines[-1] + " ..."
            else:
                lines.extend(_doc_lines(row.docs, "        "))
                lines.append("        pass")
        lines.append("")
    tree = ast.parse('\n'.join(lines) + '\n')
    return tree.body[0], lines


def operations(rows: Iterable[Door]) -> list[str]:
    """The remote operation tuple from the remote client contracts."""
    out = [SCHEMA_START, "# closed-set: generated; by=extensions/python/tools/doorgen.py; lane=door-sync", "_OPERATIONS: Final[tuple[tuple[str, str, str, str], ...]] = ("]
    for row in rows:
        if row.remote:
            remote = row.remote
            out += ["    (", *(f"        {value!r}," for value in (remote.operation, remote.request, remote.response, remote.summary)), "    ),"]
    return [*out, ")", SCHEMA_END]


def ledger_page(rows: Iterable[Door]) -> str:
    """The shrink ledger is a query over kinds and declared sugar points."""
    selected = [row for row in rows if row.owner is Owner.space and Tier.sync in row.tiers]
    counts = Counter(row.kind for row in selected)
    out = ["# The Python surface's shrink ledger", "", "Generated by `extensions/python/tools/doorgen.py` from `metta.doors`.", "", f"`Space` declares {len(selected)} core doors. Package accessor namespaces are listed in the door reference.", "", "| kind | doors |", "|---|---:|", *(f"| {kind} | {counts[kind]} |" for kind in doors.Kind), "", "A sugar fixes arguments of another door. A hand implementation may compose calls or own resources; calling another public method does not make it a parameter setting.", "", "| door | kind | implementation or longhand |", "|---|---|---|"]
    for row in selected:
        longhand = sugar_longhand(row) if row.sugar_of else (row.body.reference if row.body else "")
        out.append(f"| `{row.python}` | {row.kind} | `{longhand}` |")
    return '\n'.join(out) + '\n'


def sugar_longhand(row: Door) -> str:
    """The declared base and its fixed options, for every documentation tier."""
    if row.sugar_of is None:
        return ""
    fixed = ', '.join(f"{name}={value!r}" for name, value in row.sugar_of.fixed)
    return f"{row.sugar_of.base}(...{', ' if fixed else ''}{fixed})"


def public_declarations(row: Door) -> list[str]:
    """Print a row's complete call forms with its implicit receiver removed."""
    out = []
    for signature in row.signatures:
        node = copy.deepcopy(signature.node)
        if not row.body or row.body.receiver is not doors.Receiver.none:
            positional = node.args.posonlyargs or node.args.args
            if positional:
                positional.pop(0)
        out.extend("@" + declaration for declaration in signature.declarations
                   if declaration != "property")
        generics = f"[{signature.type_parameters}]" if signature.type_parameters else ""
        declaration = row.python if row.is_property else f"{row.python}{generics}({ast.unparse(node.args)})"
        if signature.returns:
            declaration += f" -> {signature.returns}"
        out.append(declaration)
    return out


def vocabulary_arguments(row: Door) -> list[str]:
    """Print closed option values from the vocabularies in argument types."""
    scope = {**vars(vocabularies), **vars(doors)}
    result = []
    args = row.signature.node.args
    for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs):
        if argument.annotation is None:
            continue
        choices = []
        for node in ast.walk(argument.annotation):
            kind = scope.get(node.id) if isinstance(node, ast.Name) else None
            if isinstance(kind, type) and issubclass(kind, Enum):
                choices.extend(str(value.value) for value in kind)
        if choices:
            result.append(f"`{argument.arg}`: " + ', '.join(f'`{value}`' for value in dict.fromkeys(choices)) + '.')
    return result


def door_reference(rows: Iterable[Door]) -> str:
    """All receiver families, with complete contracts and named longhands."""
    out = ["# Python door contracts", "", "Generated from `metta.doors` and workspace packages' `DOORS` declarations.", "", "The same contracts are typed `(door ...)` atoms in `&metta` at boot. `seam.publish(context)` refreshes the snapshot after registration or withdrawal.", ""]
    for row in rows:
        out.extend([f"## {row.key}", "", "```python", *public_declarations(row), "```", "", f"Kind: `{row.kind}`. Answer: `{row.answers}`. Effect: `{row.effect}`. Determinism: `{row.determinism}`.", "", f"Tiers: {', '.join(f'`{tier}`' for tier in row.tiers)}.", ""])
        options = vocabulary_arguments(row)
        if options:
            out.extend(["Declared option vocabularies:", "", *(f"- {option}" for option in options), ""])
        if row.sugar_of:
            out.extend([f"Longhand: `{sugar_longhand(row)}`.", ""])
        if row.provider:
            out.extend([f"Provider: `{row.provider.registrant}` through `seam.{row.provider.point}`, namespace `{row.provider.namespace}`.", ""])
        if row.body:
            out.extend([f"Implementation: `{row.body.reference}`, receiving `{row.body.receiver}`.", ""])
        if row.binding:
            out.extend([f"Engine binding: `{row.binding.door}`, wire `{row.binding.wire}`.", ""])
        out.extend([f"Assumes receiver state `{row.assumes.state}`.", "",
                    "| argument | MeTTa type | default | delivery | parameter kind |",
                    "|---|---|---|---|---|"])
        for argument in row.assumes.args:
            cells = (argument.name, str(argument.type.to_atom()),
                     "required" if argument.default is None else argument.default,
                     argument.delivery, argument.kind.name.lower())
            out.append("| " + " | ".join("`" + str(cell).replace("|", "\\|") + "`" for cell in cells) + " |")
        out.extend(["", f"Guarantees result type `{row.guarantees.type.to_atom()}` with the answer shape, effect, and determinism above.", ""])
        if row.refuses:
            out.extend(["Declared local refusals:", "", *(
                f"- `{refusal.kind}`: `{refusal.witness}`." for refusal in row.refuses
            ), ""])
        out.extend(["Implementation failures propagate, including failures from callees and providers.", "",
                    quote(row.docs), "", "Evidence: " + ", ".join(f"`{target}`" for target in row.evidence) + ".", ""])
    return '\n'.join(out)


def sheet(rows: Iterable[Door]) -> list[str]:
    """The consumer's complete declarations and sugar rule, from records."""
    records = tuple(rows)
    namespaces = sorted({row.provider.namespace for row in records if row.owner is Owner.namespace and row.provider})
    out = [SHEET_START, "## Python door contracts", "", "`metta.doors` is the engine-free source of host door contracts. `door-sync` checks Space, the async mirror, module and context methods, remote client and operation schemas, stubs, reference, and shrink ledger against it. The same typed rows enter `&metta` at boot; `seam.publish(context)` refreshes them after registration changes.", "", "Package doors are accessor namespaces resolved from `seam.door` rows on first access. Current workspace namespaces: " + ', '.join(f'`m.{name}`' for name in namespaces) + ".", "", "A convenience declares its base and fixed arguments. A second declaration of the same parameter point on one receiver is refused. Ownership and rollback operations keep their implementation contracts.", "", "| convenience | longhand |", "|---|---|", *(f"| `{row.key}` | `{sugar_longhand(row)}` |" for row in records if row.sugar_of), "",
           "The declarations below omit the implicit receiver. Hyphens in a MeTTa-facing door name become underscores in Python. A namespace entry `tables:add` is called as `m.tables.add(...)`; a context entry belongs to `MeTTa`. The detailed contracts, input types, delivery, refusal witnesses and tests are in `website/reference/python-door-contracts.md`.", ""]
    for owner in doors.Owner:
        selected = [row for row in records if row.owner is owner]
        if not selected:
            continue
        out.extend([f"### {owner} declarations", ""])
        for row in selected:
            out.extend([f"`{row.key}`: `{row.kind}`, returns `{row.answers}`, effect `{row.effect}`, determinism `{row.determinism}`; tiers {', '.join(f'`{tier}`' for tier in row.tiers)}.", "", "```python"])
            out.extend(public_declarations(row))
            out.extend(["```", "", row.docs.strip().splitlines()[0], ""])
            options = vocabulary_arguments(row)
            if options:
                out.extend([*(f"- {option}" for option in options), ""])
    return [*out, SHEET_END]


def projections(rows: tuple[Door, ...]) -> dict[Path, str]:
    """Direct projections, before mirror, stub, and reference dependencies."""
    out: dict[Path, str] = {}
    groups: dict[Path, set[str]] = {}
    for row in rows:
        if row.owner is Owner.namespace or row.inherited or row.body is None:
            continue
        path = module_path(row.body.module)
        name = row.body.symbol.rpartition('.')[0]
        if name and (Tier.sync in row.tiers or Tier.remote in row.tiers):
            groups.setdefault(path, set()).add(name)
    for path, classes in groups.items():
        text = path.read_text(encoding="utf-8")
        for name in sorted(classes):
            text = class_projection(text, name, rows)
        out[path] = text
    path = CORE / "_schemas.py"
    out[path] = replace_region(path.read_text(encoding="utf-8"), SCHEMA_START, SCHEMA_END, operations(rows))
    out[ROOT / "website/reference/shrink-ledger.md"] = ledger_page(rows)
    out[ROOT / "website/reference/python-door-contracts.md"] = door_reference(rows)
    out[CORE / "_door_namespaces.py"] = namespace_types(rows)
    path = CORE / "_space.py"
    keywords = next(row for row in rows if row.key == "space:eval").signature.node.args.kwonlyargs
    start, end = "# begin generated evaluation keywords", "# end generated evaluation keywords"
    out[path] = replace_region(out[path], start, end, [start,
        '# closed-set: generated; by=extensions/python/tools/doorgen.py; lane=door-sync',
        "_TERM_KEYWORDS = " + repr(tuple(arg.arg for arg in keywords)), end])
    path = ROOT / "llms.txt"
    out[path] = replace_region(path.read_text(encoding="utf-8"), SHEET_START, SHEET_END, sheet(rows))
    return out


def main(argv: list[str] | None = None) -> int:
    """Check every projection or regenerate all of them in dependency order."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--coverage", action="store_true", help="check every row's test and refusal coverage")
    parser.add_argument("--refusals", action="store_true", help="run the exact refusal witnesses declared by the rows")
    args = parser.parse_args(argv)
    problems = contract_findings()
    if problems:
        print('\n'.join(problems))
        return 1
    if args.refusals:
        witnesses = sorted({refusal.witness for row in all_rows() for refusal in row.refuses})
        command = ['sh', str(SEAT / 'test.sh'), *(str(ROOT / target) for target in witnesses)]
        print(f"door refusals: {len(witnesses)} selected test witnesses", flush=True)
        return subprocess.run(command, cwd=ROOT, env={**os.environ, 'CHECK_PY': sys.executable}, check=False).returncode  # noqa: S603 -- argv contains validated repository test witnesses
    if args.contracts or args.coverage:
        print(f"door contracts: {len(all_rows())} rows, all evidence targets resolved")
        return 0
    stale = []
    for path, wanted in projections(all_rows()).items():
        observed = path.read_text(encoding="utf-8") if path.exists() else ""
        if observed == wanted:
            continue
        if args.write:
            path.write_text(wanted, encoding="utf-8")
        else:
            stale.append(str(path.relative_to(ROOT)))
    import aiogen  # noqa: PLC0415  -- the mirror backend
    import initstubgen  # noqa: PLC0415  -- the stub backend
    import reference  # noqa: PLC0415  -- the reference backend

    flags = ["--write"] if args.write else []
    for name, backend in (("mirrors", aiogen), ("stub", initstubgen), ("reference", reference)):
        if backend.main(flags):
            stale.append(name)
    if stale:
        print("door-sync: stale projections: " + ', '.join(stale))
        print("run python extensions/python/tools/doorgen.py --write")
        return 1
    print(f"door-sync: {len(all_rows())} contracts and every projection agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
