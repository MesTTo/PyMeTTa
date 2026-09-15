"""Purpose: generate host surfaces from the typed Python door contracts.

Assumes: implementations remain in the modules their rows name.
Guarantees: changed membership, signatures, sugar points, or evidence cannot
  leave a stale projection unnoticed [tested:
  test_every_door_projection_is_current,
  test_door_sync_detects_a_planted_change_in_each_projection; commit=WORKTREE].
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
from dataclasses import fields, replace
from enum import Enum
from functools import lru_cache
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
SEAT = ROOT / "extensions/python"
CORE = SEAT / "metta"
sys.path[:0] = [str(SEAT), str(TOOLS)]

from prologmacros import scoped_goal_expansions  # noqa: E402
from reference import quote, split_top_level  # noqa: E402

from metta import doors, vocabularies  # noqa: E402 -- the engine-free row grammar
from metta._errors.refusals import REFUSALS  # noqa: E402
from metta.doors import Door, Owner, Signature, Tier  # noqa: E402
from metta.doors._scan import core, is_mark, scan  # noqa: E402 -- the shared declaration reader
from metta.doors._scan import signature as _signature  # noqa: E402 -- the shared declaration reader

START = "    # begin generated doors: "
END = "    # end generated doors: "
SCHEMA_START = "# begin generated remote operations"
SCHEMA_END = "# end generated remote operations"
SHEET_START = "<!-- begin generated door contracts -->"
SHEET_END = "<!-- end generated door contracts -->"
ATOM_OPERATORS_START = "<!-- begin generated atom operators -->"
ATOM_OPERATORS_END = "<!-- end generated atom operators -->"


def module_path(name: str, root: Path = ROOT) -> Path:
    """Locate a core or workspace module without importing it."""
    seat = root / "extensions/python"
    if name.startswith("metta."):
        path = seat / (name.replace(".", "/") + ".py")
        if path.is_file():
            return path
        package = seat / name.replace(".", "/") / "__init__.py"
        if package.is_file():
            return package
    found = [path for path in (seat / "ext").glob("metta-*/*.py") if path.stem == name]
    if len(found) != 1:
        msg = f"door implementation module {name!r} has {len(found)} source files"
        raise ValueError(msg)
    return found[0]


def package_rows(root: Path = ROOT) -> tuple[Door, ...]:
    """Read extension marks with the same source reader used by core discovery."""
    return tuple(row for path in sorted((root / "extensions/python/ext").glob("metta-*/*.py"))
                 for row in scan(path, path.stem))


def all_rows(root: Path = ROOT) -> tuple[Door, ...]:
    """Discover core and workspace declarations without loading their bodies."""
    return doors.validate((*core(root / "extensions/python/metta"), *package_rows(root)))


def _canonical(text: str | None) -> str | None:
    if text is None:
        return None
    return ast.unparse(ast.parse(text, mode="eval").body)


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
    if row.is_property:
        nodes = [node for node in nodes if not any(
            isinstance(item, ast.Attribute) and item.attr in {'setter', 'deleter'}
            for item in node.decorator_list
        )]
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
    """A public method on a door-owning class carries its contract beside it."""
    classes = {(row.body.module, row.body.symbol.rpartition('.')[0]) for row in rows
               if row.body and '.' in row.body.symbol and row.owner is not Owner.namespace}
    found = []
    for module, name in sorted(classes):
        path = module_path(module, root)
        held = ast.parse(path.read_text(encoding="utf-8"), filename=str(path)).body
        for part in name.split('.'):
            held = next(node.body for node in held if isinstance(node, ast.ClassDef) and node.name == part)
        found.extend(
            f"{module}:{name}.{node.name}: public implementation has no door mark"
            for node in held
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith('_')
            and not any(is_mark(item) or ast.unparse(item) == 'overload'
                        or (isinstance(item, ast.Attribute) and item.attr in {'setter', 'deleter'})
                        for item in node.decorator_list)
        )
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
    definition_shadow = name in vars(builtins) and not indent
    if len(head) <= 100:
        codes = [*(('A001',) if definition_shadow else ()), *(('A002',) if shadowed else ())]
        note = f"  # noqa: {', '.join(codes)} -- the declared public spelling" if codes else ""
        return [head + ignored + note]
    return [
        f"{indent}def {name}{generics}(" + ignored + ("  # noqa: A001 -- the declared public spelling" if definition_shadow else ""),
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
    records = tuple(rows)
    selected = [row for row in records if row.owner is Owner.namespace and row.body]
    result_rows = [row for row in records if row.owner in {Owner.rows, Owner.answers}
                   and row.body and not row.body.module.startswith('metta.')]
    modules = {name: f"_body_{index}" for index, name in enumerate(sorted({row.body.module for row in (*selected, *result_rows)}))}
    out = [
        '"""Purpose: type the accessor namespaces declared by installed workspace packages.',
        '', 'Generated by tools/doorgen.py from door rows.', '"""', '',
        'from __future__ import annotations', '', 'from typing import TYPE_CHECKING, Protocol', '',
    ]
    if modules or result_rows:
        out.append('if TYPE_CHECKING:')
    if result_rows:
        out.append('    import metta._spaces.results as _results')
    for local in (False, True):
        # Optional packages can be absent in a core-only typing environment.
        # The specific import guard preserves their types when installed:
        # https://github.com/python/mypy/blob/v2.3.0/docs/source/error_code_list2.rst#check-that-type-ignore-comment-is-used-unused-ignore
        guard = '' if local else '  # type: ignore[import-not-found, unused-ignore]  # ty: ignore[unresolved-import] -- optional provider declarations remain typed when installed'
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
                    if not row.docs:
                        out.append('        ...')
                    out.append('')
    for row in result_rows:
        for signature in row.signatures:
            node = copy.deepcopy(signature.node)
            qualifier = _QualifyAnnotation(modules[row.body.module])
            args = qualifier.visit(node.args)
            first = (args.posonlyargs or args.args)[0]
            first.annotation = ast.parse('_results.' + row.owner.value.title(), mode='eval').body
            args.defaults = [ast.Constant(Ellipsis) for _ in args.defaults]
            args.kw_defaults = [None if value is None else ast.Constant(Ellipsis) for value in args.kw_defaults]
            projected = replace(signature, parameters=ast.unparse(args), returns=ast.unparse(qualifier.visit(node.returns)) if node.returns else None)
            declaration = signature_lines(projected, '_' + row.owner.value + '_' + row.python, '')
            declaration[0] += '  # pylint: disable=unused-argument # signature-only extension declaration'
            out.extend(['', *declaration])
            out.extend(_doc_lines(row.docs, '    '))
            if not row.docs:
                out.append('    ...')
    # The emitter reads this tool's source helpers.
    from doorfaces import clean_imports  # noqa: PLC0415

    return clean_imports('\n'.join(out) + '\n', CORE / 'doors/_namespaces.py')


def declared_annotation_imports(path: Path) -> set[tuple[str, int]]:
    """Provider imports belong only to the exact generated annotation file."""
    if path != CORE / 'doors/_namespaces.py':
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


def atom_operator_table() -> list[str]:
    """Pair each source spelling with the existing atom policy's built term."""
    # Atom construction is needed only for this projection.
    from metta._atoms._python_protocols import BY_FORM  # noqa: PLC0415
    from metta._atoms.model import Symbol, _apply_operator_lowering  # noqa: PLC0415
    from metta._atoms.operators import OPERATOR_LOWERINGS, selector  # noqa: PLC0415

    out = [ATOM_OPERATORS_START,
           "<!-- Generated by extensions/python/tools/doorgen.py from OPERATOR_LOWERINGS. -->",
           "", "| you write | it builds |", "|---|---|"]
    for entry in OPERATOR_LOWERINGS:
        names = tuple(f"x{index}" for index in range(1, entry.arity + 1))
        operands = tuple(Symbol(name) for name in names)
        if entry.kind == "taken":
            method = selector(entry)
            syntax = f"{names[0]}.{method}({', '.join(names[1:])})"
            image = getattr(type(operands[0]), method)(*operands)
        else:
            form = BY_FORM.get(entry.source.callable)
            parameters = form.parameters if form is not None else names
            renames = dict(zip(parameters, names, strict=True))
            tree = ast.parse(entry.syntax, mode="eval")
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    node.id = renames.get(node.id, node.id)
            syntax = ast.unparse(tree)
            image = _apply_operator_lowering(entry, *operands)
        cells = (cell.replace("|", "\\|") for cell in (syntax, str(image)))
        out.append("| " + " | ".join(f"`{cell}`" for cell in cells) + " |")
    return [*out, "", ATOM_OPERATORS_END]


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
    out = ["# Python door contracts", "", "Generated by `extensions/python/tools/doorgen.py` from `@door` marks beside core and provider bodies.", "", "The same contracts are typed `(door ...)` atoms in `&metta` at boot. `seam.publish(context)` refreshes the snapshot after registration or withdrawal.", ""]
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
            if row.binding.evaluation is not None:
                out.extend(["| evaluation field | default | meaning |", "|---|---|---|"])
                for field in fields(row.binding.evaluation):
                    value = getattr(row.binding.evaluation, field.name)
                    out.append(f"| `{field.name}` | `{value!s}` | {field.metadata['means']} |")
                out.append("")
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


def evaluation_projections(rows: tuple[Door, ...]) -> dict[Path, str]:
    """Compile the door grammar to Janus tuples and scoped source constructors."""
    grammar = fields(doors.EvaluationOptions)

    def python_value(value: object, *, bound: bool = False) -> str:
        if isinstance(value, Enum):
            return repr(value.value)
        if value is None or (bound and value < 0):
            return repr('none')
        if isinstance(value, bool):
            return repr('true' if value else 'false')
        if isinstance(value, tuple):
            return repr(list(value))
        return repr(value)

    python = ['"""Generated by tools/doorgen.py from Door.Binding.evaluation."""', '',
              'from typing import Any, NamedTuple', '', '', 'class EvaluationRecord(NamedTuple):',
              '    """The fixed Janus record; its field order comes from EvaluationOptions."""', '']
    for field in grammar:
        value = field.default
        bound = field.metadata.get('bound', False)
        annotation = ('str' if isinstance(value, (Enum, bool)) else 'list[Any]' if isinstance(value, tuple)
                      else 'list[Any] | str' if value is None else
                      f'{type(value).__name__} | str' if bound else type(value).__name__)
        python.append(f'    {field.name}: {annotation}')
    bounds = tuple(field.name for field in grammar if field.metadata.get('bound'))
    python.extend(['', '    def with_options(self, **options: Any) -> "EvaluationRecord":',
                   '        """Project Python flags and unbounded quotas to native Prolog atoms."""',
                   '        native: dict[str, Any] = {',
                   '            name: ("none" if value is None else',
                   '                   "true" if value is True else "false" if value is False else',
                   f'                   "none" if name in {bounds!r} and isinstance(value, (int, float)) and value < 0 else value)',
                   '            for name, value in options.items()',
                   '        }',
                   '        return self._replace(**native)  # pylint: disable=no-member # NamedTuple supplies _replace; the binding interface tests execute it'])
    python.extend(['', '', '# closed-set: generated; by=extensions/python/tools/doorgen.py; lane=door-sync',
                   'EVALUATIONS = {'])
    evaluations = tuple(row for row in rows if row.binding is not None and row.binding.evaluation is not None)
    for index, row in enumerate(evaluations):
        values = ', '.join(f'{field.name}={python_value(getattr(row.binding.evaluation, field.name), bound=field.metadata.get("bound", False))}'
                           for field in grammar)
        python.append(f'    {row.key!r}: ({row.binding.door!r}, EvaluationRecord({values}), {index}),')
    python.extend(['}', ''])
    prolog = ['% Generated by tools/doorgen.py from Door.Binding.evaluation.',
              ':- module(metta_python_options, [binding_options_expansion/2, evaluation_preset/2]).',
              ':- use_module(library(error), [domain_error/2]).',
              ':- use_module(library(lists), [member/2, numlist/3]).',
              ':- use_module(library(apply), [maplist/2]).', '',
              f'evaluation_arity({len(grammar)}).']
    for index, field in enumerate(grammar, 1):
        prolog.append(f'evaluation_field({field.name}, {index}, {python_value(field.default, bound=field.metadata.get("bound", False))}).')
    prolog.extend(f'evaluation_bound({field.name}).' for field in grammar if field.metadata.get('bound'))
    for index, row in enumerate(evaluations):
        values = ', '.join(python_value(getattr(row.binding.evaluation, field.name), bound=field.metadata.get('bound', False))
                           for field in grammar)
        prolog.append(f"evaluation_preset({index}, '-'({values})).")
    # SWI recommends an imported sentinel to scope global expansion hooks:
    # https://www.swi-prolog.org/pldoc/man?section=progtransform (SWI 10.1.13).
    prolog.extend(scoped_goal_expansions('metta_python_options', 'binding_options_expansion', (
        ('metta_py_options(Record, Fields)', 'Record = Shape',
         '    is_list(Fields),\n    evaluation_shape(Fields, Shape)'),
        ('metta_py_option_record(Fields, Record)', 'Record = Shape',
         '    is_list(Fields),\n    evaluation_record(Fields, Shape)'),
        ('metta_py_evaluate(Fields, Space, Target, Result)',
         'metta_py_evaluate(Record, Space, Target, Result)',
         '    is_list(Fields),\n    evaluation_record(Fields, Record)'),
        ('metta_py_option_limits(Time, Inf, Seconds, Inferences)',
         '((Time == none -> Seconds = -1.0 ; Seconds = Time),\n'
         '                           (Inf == none -> Inferences = -1 ; Inferences = Inf))', ''),
    )).splitlines())
    prolog.extend('''
evaluation_shape(Fields, Record) :-
    evaluation_arity(Arity),
    functor(Record, -, Arity),
    evaluation_put(Fields, [], Record).

evaluation_put([], _, _).
evaluation_put([Field|Fields], Seen, Record) :-
    ( compound(Field), compound_name_arguments(Field, Name, [Value]),
      evaluation_field(Name, Position, _)
    -> ( member(Name, Seen) -> domain_error(distinct_evaluation_field, Name)
       ; ( evaluation_bound(Name), number(Value), Value < 0
         -> arg(Position, Record, none)
         ; arg(Position, Record, Value) ),
         evaluation_put(Fields, [Name|Seen], Record) )
    ; domain_error(evaluation_field, Field)
    ).

evaluation_record(Fields, Record) :-
    evaluation_shape(Fields, Record),
    evaluation_arity(Arity),
    numlist(1, Arity, Positions),
    maplist(evaluation_default(Record, Fields), Positions).

evaluation_default(Record, Fields, Position) :-
    evaluation_field(Name, Position, Default),
    ( member(Field, Fields), compound_name_arguments(Field, Name, [_])
    -> true
    ; arg(Position, Record, Default)
    ).

'''.strip('\n').splitlines())
    return {CORE / '_binding/options.py': '\n'.join(python),
            CORE / '_binding/options.pl': '\n'.join(prolog) + '\n'}


def projections(rows: tuple[Door, ...]) -> dict[Path, str]:
    """Project marked implementations through the one face emitter."""
    import doorfaces  # noqa: PLC0415 -- the emitter reads this tool's source helpers
    import protocolgen  # noqa: PLC0415 -- protocol facts share artifact ownership and source validation
    import rootgen  # noqa: PLC0415 -- root declarations share the same emitter

    out = {**doorfaces.synchronous(rows, ROOT), **doorfaces.asynchronous(rows, ROOT), **rootgen.projections(rows), **evaluation_projections(rows), **protocolgen.projections(ROOT)}
    path = CORE / 'remote/_schemas.py'
    out[path] = replace_region(path.read_text(encoding="utf-8"), SCHEMA_START, SCHEMA_END, operations(rows))
    out[ROOT / "website/reference/shrink-ledger.md"] = ledger_page(rows)
    out[ROOT / "website/reference/python-door-contracts.md"] = door_reference(rows)
    path = ROOT / "website/guide/atoms-terms.md"
    out[path] = replace_region(path.read_text(encoding="utf-8"), ATOM_OPERATORS_START, ATOM_OPERATORS_END, atom_operator_table())
    out[CORE / 'doors/_namespaces.py'] = namespace_types(rows)
    path = CORE / '_spaces/results.py'
    text = path.read_text(encoding='utf-8')
    for owner in (Owner.rows, Owner.answers):
        name = owner.value.title()
        start, end = f'    # begin generated extension declarations: {name}', f'    # end generated extension declarations: {name}'
        aliases = [f'        {row.python} = _door_types._{owner.value}_{row.python}' for row in rows
                   if row.owner is owner and row.body and not row.body.module.startswith('metta.')]
        content = [start, '    # Generated by tools/doorgen.py from extension door marks.', '    if TYPE_CHECKING:', *(aliases or ['        pass']), end]
        text = replace_region(text, start, end, content)
    out[path] = text
    path = CORE / '_spaces/execution.py'
    keywords = next(row for row in rows if row.key == "space:eval").signature.node.args.kwonlyargs
    start, end = "# begin generated evaluation keywords", "# end generated evaluation keywords"
    out[path] = replace_region(path.read_text(encoding='utf-8'), start, end, [start,
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
    import reference  # noqa: PLC0415  -- the reference backend

    flags = ["--write"] if args.write else []
    for name, backend in (("reference", reference),):
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
