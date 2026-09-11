"""Purpose: read door marks and their Python declarations without loading bodies.

Guarantees: metadata executes only the door record grammar; importing a marked
body is unnecessary for discovery [source:
extensions/python/metta/doors/_scan.py:154; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import is_dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeGuard

import metta.doors as _doors
from metta.doors import Body, Door, Family, Owner, Receiver, Signature


def signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    ignores: tuple[str, ...] = (),
) -> Signature:
    """Read a complete declaration, excluding its metadata mark."""
    return Signature(
        ast.unparse(node.args), ast.unparse(node.returns) if node.returns else None,
        ', '.join(ast.unparse(parameter) for parameter in node.type_params),
        tuple(ast.unparse(item) for item in node.decorator_list if not is_mark(item)),
        ignores,
    )


def is_mark(node: ast.AST) -> TypeGuard[ast.Call]:
    """Recognize the decorator call independently of its imported alias."""
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == 'door')
        or (isinstance(node.func, ast.Attribute) and node.func.attr == 'door')
    )


class _Unqualify(ast.NodeTransformer):
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        # policy-inventory-exempt: mechanism-internal; reason=door metadata grammar admits qualified and private-qualified record constructors; evidence=extensions/python/metta/doors/_scan.py:contract
        if isinstance(node.value, ast.Name) and node.value.id in {'_doors', 'doors'}:
            return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return self.generic_visit(node)


def contract(mark: ast.Call, path: Path) -> dict[str, Any]:
    """Evaluate checked literals and record constructors, never package code."""
    scope = {name: value for name, value in vars(_doors).items()
             if isinstance(value, type) and (is_dataclass(value) or issubclass(value, Enum))}
    if len(mark.args) > 1 or any(item.arg is None for item in mark.keywords):
        msg = f'{path}: a door mark supplies one kind and named contract fields'
        raise ValueError(msg)
    expressions = {item.arg: item.value for item in mark.keywords if item.arg is not None}
    if mark.args:
        if 'kind' in expressions:
            msg = f'{path}: a door mark supplied kind twice'
            raise ValueError(msg)
        expressions['kind'] = mark.args[0]
    result = {}
    for name, declared in expressions.items():
        expression = _Unqualify().visit(declared)
        for item in ast.walk(expression):
            valid = isinstance(item, (ast.Tuple, ast.List, ast.Constant, ast.Load, ast.keyword))
            if isinstance(item, ast.Name):
                valid = item.id in scope
            elif isinstance(item, ast.Call):
                valid = isinstance(item.func, ast.Name) and item.func.id in scope
            elif isinstance(item, ast.Attribute):
                valid = (isinstance(item.value, ast.Name) and item.value.id in scope
                         and issubclass(scope[item.value.id], Enum) and not item.attr.startswith('_'))
            elif isinstance(item, (ast.UnaryOp, ast.USub, ast.UAdd)):
                valid = True
            if not valid:
                msg = f'{path}: door metadata reads outside the row grammar: {ast.unparse(item)}'
                raise ValueError(msg)
        result[name] = eval(compile(ast.fix_missing_locations(ast.Expression(expression)), str(path), 'eval'), {'__builtins__': {}} | scope)  # noqa: S307  # nosec B307  # pylint: disable=eval-used # the complete expression grammar is checked above
    return result


def _owner(class_name: str, first: ast.arg | None, values: dict[str, Any]) -> Owner:
    if values.get('provider') is not None and values.get('sugar_of') is None:
        return Owner.namespace
    spelling = class_name.rsplit('.', 1)[-1]
    # policy-inventory-exempt: mechanism-internal; reason=source receiver class spellings are parsed without importing their implementations; evidence=extensions/python/metta/doors/_scan.py:_owner
    if spelling not in {'Space', 'SpaceHandle', '_SpaceT', 'MeTTa', 'MeTTaBase', 'Rows', 'Answers', 'RemoteSpace', 'RemoteCursor'} and first is not None:
        spelling = ast.unparse(first.annotation).strip("'\"").rsplit('.', 1)[-1] if first.annotation else ''
        spelling = spelling.split('[', 1)[0]
    # policy-inventory-exempt: mechanism-internal; reason=concrete and generic space receiver spellings in Python source; evidence=extensions/python/metta/doors/_scan.py:_owner
    if spelling in {'Space', 'SpaceHandle', '_SpaceT'}:
        return Owner.space
    # policy-inventory-exempt: mechanism-internal; reason=public and handwritten context class spellings in Python source; evidence=extensions/python/metta/doors/_scan.py:_owner
    if spelling in {'MeTTa', 'MeTTaBase'}:
        return Owner.context
    if spelling == 'Rows':
        return Owner.rows
    if spelling == 'Answers':
        return Owner.answers
    if spelling == 'RemoteSpace':
        return Owner.remote_space
    if spelling == 'RemoteCursor':
        return Owner.remote_cursor
    if values.get('provider') is not None:
        return Owner.namespace
    msg = f'a door receiver has no declared family: {spelling!r}'
    raise ValueError(msg)


@lru_cache(maxsize=512)
def _read(path: Path, module: str, _modified: int, _size: int) -> tuple[Door, ...]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text, filename=str(path), type_comments=True)
    ignores = {
        item.lineno: tuple(part.strip() for part in item.tag.strip('[]').split(','))
        for item in tree.type_ignores
    }
    result = []

    def visit(nodes: list[ast.stmt], class_name: str = '') -> None:
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                visit(node.body, '.'.join(filter(None, (class_name, node.name))))
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            marks = [item for item in node.decorator_list if is_mark(item)]
            if not marks:
                continue
            if len(marks) != 1:
                msg = f'{path}:{node.lineno}: one body carries more than one door mark'
                raise ValueError(msg)
            values = contract(marks[0], path)
            first = next(iter([*node.args.posonlyargs, *node.args.args]), None)
            owner = _owner(class_name, first, values)
            static = any(isinstance(item, ast.Name) and item.id == 'staticmethod' for item in node.decorator_list)
            annotation = ast.unparse(first.annotation).strip("'\"").rsplit('.', 1)[-1] if first is not None and first.annotation else ''
            receiver = Receiver.method if class_name and not static else (
                # policy-inventory-exempt: mechanism-internal; reason=annotated space arguments identify the source call shape; evidence=extensions/python/metta/doors/_scan.py:_read
                Receiver.space if owner.family is Family.core or annotation in {'Space', 'SpaceLike', '_SpaceT', 'MeTTa'}
                # policy-inventory-exempt: mechanism-internal; reason=conventional receiver parameter names identify the source call shape; evidence=extensions/python/metta/doors/_scan.py:_read
                or (first is not None and first.arg in {'space', 'receiver'})
                else Receiver.value if owner.family is Family.result else Receiver.none
            )
            declarations = [item for item in nodes if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == node.name and item.lineno <= node.lineno]
            rows = tuple(signature(item, ignores.get(item.lineno, ())) for item in declarations)
            result.append(Door(
                owner=owner, name=node.name if node.name.startswith('__') else node.name.replace('_', '-'),
                signatures=rows, body=Body(module, '.'.join(filter(None, (class_name, node.name))), receiver),
                docs=inspect.cleandoc(ast.get_docstring(node, clean=False) or ''), **values,
            ))

    visit(tree.body)
    return tuple(result)


def scan(path: Path, module: str) -> tuple[Door, ...]:
    """Read a source snapshot, caching it by identity, modification and size."""
    stat = path.stat()
    return _read(path, module, stat.st_mtime_ns, stat.st_size)


def core_paths(root: Path | None = None) -> tuple[tuple[Path, str], ...]:
    """The shipped package lattice determines the source discovery boundary."""
    from metta._layers import BUILDS_ON  # noqa: PLC0415 -- a schema discovery projection

    root = Path(__file__).resolve().parent.parent if root is None else root
    result = []
    for name in BUILDS_ON:
        path = root if name == 'metta' else root / name
        sources = [root / '__init__.py'] if name == 'metta' else sorted(path.rglob('*.py')) if path.is_dir() else [path.with_suffix('.py')]
        for source in sources:
            if source.is_file():
                module = 'metta.' + '.'.join(source.relative_to(root).with_suffix('').parts)
                result.append((source, module.removesuffix('.__init__')))
    return tuple(result)


def core(root: Path | None = None) -> tuple[Door, ...]:
    """Read core-owned marks; provider marks enter through seam registration."""
    return tuple(row for path, module in core_paths(root) for row in scan(path, module) if row.provider is None)
