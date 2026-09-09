"""Purpose: emit each Python door face from the same marked implementation.

Polars' expr_dispatch installs methods at class construction, but its
call_expr function returns a wrapper. Directly binding unmodified body
functions as descriptors is the zero-forwarder-frame alternative considered
here. Source forwarders retain explicit calls that mypy can check. The
readability ruling selects this shape unless the recorded measurements demand
otherwise. The inspected precedent is immutable:
https://github.com/pola-rs/polars/blob/b4755d7ad1d3e9c42fc3711a09961fff492fe46c/py-polars/polars/series/utils.py

Decides: foundation calls bind directly and higher calls use lazy modules;
the package lattice decides which applies [source:
extensions/python/metta/_layers.py:107; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import ast
import builtins
import copy
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from metta._layers import binding_mode
from metta.doors import Door, Owner, Receiver, Signature, Tier


def clean_imports(source: str, path: Path) -> str:
    """Normalize generated imports with the repository's existing Ruff tool."""
    # Generated-code import normalization follows apply_ruff_lint in:
    # https://github.com/koxudaxi/datamodel-code-generator/blob/b71a7a8f9270faee821d45bcd16ff64af8f5416f/src/datamodel_code_generator/format.py
    result = subprocess.run(  # noqa: S603 -- fixed argv; generated source is stdin, never shell text
        [sys.executable, "-m", "ruff", "check", "--isolated", "--select",
         "I,F401,F811,PLC0414,PLR0402,RUF022", "--fix", "--unsafe-fixes",
         "--config", 'lint.isort.known-first-party = ["metta"]',
         # Every generated export is explicit. Ruff's __init__.py heuristic
         # cannot remove unused private imports, unlike its ordinary-module rule.
         "--stdin-filename", "generated" + path.suffix, "-"],
        input=source, capture_output=True, text=True, check=False,
    )
    if result.returncode:
        message = f"generated imports did not normalize: {result.stderr}"
        raise RuntimeError(message)
    return result.stdout.rstrip("\n") + "\n"


def _bindings(module: str, root: Path) -> dict[str, tuple[str, str | None]]:
    from doorgen import module_path  # noqa: PLC0415 -- emitter/reader cycle

    path = module_path(module, root)
    return _source_bindings(module, path, path.read_text(encoding='utf-8'))


@lru_cache(maxsize=256)
def _source_bindings(module: str, path: Path, source: str) -> dict[str, tuple[str, str | None]]:
    tree = ast.parse(source)
    result = {}

    def scope(nodes: list[ast.stmt]) -> Iterable[ast.stmt]:
        for node in nodes:
            yield node
            if isinstance(node, ast.If):
                yield from scope(node.body)
                yield from scope(node.orelse)
            elif isinstance(node, (ast.Try, ast.TryStar)):
                yield from scope(node.body)
                yield from scope(node.orelse)
                yield from scope(node.finalbody)
                for handler in node.handlers:
                    yield from scope(handler.body)

    for node in scope(tree.body):
        if isinstance(node, ast.ImportFrom):
            source = node.module or ''
            if node.level:
                parent = module if path.name == '__init__.py' else module.rpartition('.')[0]
                source = '.'.join([*parent.split('.')[:len(parent.split('.')) - node.level + 1], *([source] if source else [])])
            for alias in node.names:
                result[alias.asname or alias.name] = (source, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name.split('.')[0]] = (alias.name if alias.asname else alias.name.split('.')[0], None)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = (module, node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result[target.id] = (module, target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result[node.target.id] = (module, node.target.id)
    return result


class Emitter:
    """One signature, overload, documentation and invocation emitter."""

    def __init__(self, root: Path, module: str, importer: str, *, namespace: str = "") -> None:
        """Collect the imports and callable contracts required by one face."""
        self.root = root
        self.module = module
        self.importer = importer
        self.namespace = namespace
        self.imports: dict[str, str] = {}
        self.early: set[str] = set()
        self.protocols: list[str] = []

    def binding(self, module: str, *, early: bool = False) -> str:
        """Name an implementation module for calls and runtime annotations."""
        if module == self.module:
            return ''
        if early:
            self.early.add(module)
        alias = '_body_' + module.replace('.', '_')
        self.imports[module] = alias
        return self.namespace + "." + alias if self.namespace else alias

    def qualified(self, reference: tuple[str, str | None], *, early: bool = False) -> str:
        """Resolve an imported name in the generated module's namespace."""
        module, name = reference
        if name is None:
            return self.binding(module, early=early)
        if module == 'builtins':
            return '_builtins.' + name
        if module == self.module:
            return self.namespace + "." + name if self.namespace else name
        return self.binding(module, early=early) + '.' + name

    def expression(self, node: ast.expr | None, source: str, *, local: set[str] = frozenset(), early: bool = False) -> ast.expr | None:
        """Move annotations and defaults while retaining their original bindings."""
        if node is None:
            return None
        bindings = _bindings(source, self.root)
        emitter = self

        class Names(ast.NodeTransformer):
            def visit_Attribute(self, item: ast.Attribute) -> ast.AST:
                if isinstance(item.value, ast.Name) and bindings.get(item.value.id) == (emitter.module, None):
                    return ast.parse(emitter.qualified((emitter.module, item.attr)), mode="eval").body
                return self.generic_visit(item)

            def visit_Name(self, item: ast.Name) -> ast.AST:
                if item.id in local:
                    return item
                if item.id in bindings:
                    return ast.parse(emitter.qualified(bindings[item.id], early=early), mode='eval').body
                if item.id in vars(builtins):
                    return ast.parse('_builtins.' + item.id, mode='eval').body
                if item.id == 'Self':
                    return ast.Name(id='Self', ctx=ast.Load())
                msg = f'{source}: annotation or default has no declaration for {item.id!r}'
                raise ValueError(msg)

        return Names().visit(copy.deepcopy(node))

    def declaration(self, row: Door, signature: Signature, tier: str) -> Signature:
        """Project a body's receiver and annotations onto one public tier."""
        assert row.body is not None
        node = copy.deepcopy(signature.node)
        args = node.args
        first = args.posonlyargs or args.args
        receiver = row.body.receiver is not Receiver.none
        if receiver and first:
            if tier == 'module':
                first.pop(0)
            else:
                first[0].arg = 'self'
                if tier != 'sync':
                    first[0].annotation = None
        elif tier != 'module':
            args.args.insert(0, ast.arg(arg='self'))
        local = {getattr(parameter, 'name', '') for parameter in node.type_params}
        for parameter in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                          *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])]:
            parameter.annotation = self.expression(parameter.annotation, row.body.module, local=local)
        args.defaults = [self.expression(value, row.body.module, local=local, early=True) for value in args.defaults]
        args.kw_defaults = [self.expression(value, row.body.module, local=local, early=True) for value in args.kw_defaults]
        node.returns = self.expression(node.returns, row.body.module, local=local)
        if row.context_inplace and tier == 'context':
            node.returns = ast.Name(id='_Self', ctx=ast.Load())
        declarations = tuple(
            declaration if declaration == 'overload' else ast.unparse(self.expression(ast.parse(declaration, mode='eval').body, row.body.module, early=True))
            for declaration in signature.declarations
            if declaration not in {'staticmethod', 'property'}
            and not (tier == 'async' and declaration.startswith('dataclass_transform'))
        )
        if row.is_property and tier == 'sync':
            declarations = ('property', *declarations)
        ignores = signature.type_ignores
        if row.context_inplace and tier == 'sync':
            ignores = tuple(dict.fromkeys((*ignores, 'override')))
        return replace(signature, parameters=ast.unparse(args), returns=ast.unparse(node.returns) if node.returns else None, declarations=declarations, type_ignores=ignores)

    @staticmethod
    def arguments(signature: Signature, *, receiver: bool = True) -> str:
        """Forward every parameter with its positional or keyword convention."""
        args = signature.node.args
        positional = [argument.arg for argument in [*args.posonlyargs, *args.args]]
        if receiver:
            positional = positional[1:]
        if args.vararg:
            positional.append('*' + args.vararg.arg)
        positional.extend(argument.arg + '=' + argument.arg for argument in args.kwonlyargs)
        if args.kwarg:
            positional.append('**' + args.kwarg.arg)
        return ', '.join(positional)

    def _protocol(self, row: Door, signature: Signature, *, bound: bool) -> str:
        from doorgen import signature_lines  # noqa: PLC0415 -- the reader calls this emitter

        words = (row.owner.value + '_' + row.python).replace('-', '_').split('_')
        name = '_Implementation' + ''.join(word.capitalize() for word in words) + ('Bound' if bound else '')
        args = copy.deepcopy(signature.node.args)
        first = args.posonlyargs or args.args
        if bound:
            first.pop(0)
        else:
            original = row.signature.node.args
            original_receiver = (original.posonlyargs or original.args)[0]
            first[0].annotation = self.expression(original_receiver.annotation, row.body.module)
            # Forwarders pass the body receiver positionally. Its name is not
            # part of the callback protocol's keyword contract.
            # https://github.com/python/mypy/blob/v2.3.0/docs/source/protocols.rst#callback-protocols
            occupied = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
            receiver_name = '_receiver'
            while receiver_name in occupied:
                receiver_name += '_'
            first[0].arg = receiver_name
            if not args.posonlyargs:
                args.posonlyargs.append(args.args.pop(0))
        args.posonlyargs.insert(0, ast.arg(arg='self'))
        declared = replace(signature, parameters=ast.unparse(args), declarations=())
        lines = ['class ' + name + '(_Protocol):', *signature_lines(declared, '__call__')]
        lines.append('        ...')
        self.protocols.append('\n'.join(lines))
        return name

    def method(self, row: Door, tier: str, *, name: str | None = None, stub: bool = False) -> str:
        """Emit overloads and a typed call to the marked implementation."""
        from doorgen import (  # noqa: PLC0415 -- emitter/reader cycle
            _doc_lines,
            signature_lines,
        )

        assert row.body is not None
        public = name or row.python
        signatures = row.signatures
        if tier == 'async' and row.async_signature is not None:
            signatures = (row.async_signature,)
        indent = '' if tier == 'module' else '    '
        lines = []
        for signature in signatures:
            if stub and len(signatures) > 1 and 'overload' not in signature.declarations:
                continue
            declared = self.declaration(row, signature, tier)
            if stub:
                args = declared.node.args
                args.defaults = [ast.Constant(Ellipsis) for _ in args.defaults]
                args.kw_defaults = [None if value is None else ast.Constant(Ellipsis) for value in args.kw_defaults]
                declared = replace(declared, parameters=ast.unparse(args))
            lines.extend(indent + '@' + ('_overload' if decorator == 'overload' else decorator)
                         for decorator in declared.declarations)
            header = signature_lines(declared, public, indent)
            if tier == 'async':
                header[0] = header[0].replace('def ', 'async def ', 1)
            lines.extend(header)
            if stub or 'overload' in declared.declarations:
                lines.append(indent + '    ...')
                continue
            note = 'Runs against the default context\'s self space.' if tier == 'module' else 'Runs against this context\'s self space.' if tier == 'context' else ''
            docs = row.docs + ('\n\n' + note if note else '')
            lines.extend(_doc_lines(docs, indent + '    '))
            arguments = self.arguments(declared, receiver=tier != 'module')
            if tier == 'sync':
                alias = self.binding(row.body.module)
                target = alias + '.' + row.body.symbol
                supplied = ', '.join(filter(None, ('self', arguments)))
                if len(row.signatures) > 1:
                    full = self.declaration(row, row.signature, 'sync')
                    # The source implementation accepts its complete union of
                    # arguments. Public overloads intentionally hide that union.
                    protocol = self._protocol(row, full, bound=False)
                    target = f'_cast({protocol}, {target})'
                call = target + '(' + supplied + ')'
            else:
                receiver = 'engine().self' if tier == 'module' else 'self.self' if tier == 'context' else 'm'
                target = receiver + '.' + row.python
                if tier == 'async' and row.owner is Owner.namespace:
                    target = receiver + '.' + row.provider.namespace + '.' + row.python
                elif tier == 'async' and Tier.sync not in row.tiers:
                    alias = self.binding(row.body.module)
                    target = alias + '.' + row.body.symbol
                    arguments = ', '.join(filter(None, ('m', arguments)))
                elif len(row.signatures) > 1:
                    full = self.declaration(row, row.signature, 'sync')
                    protocol = self._protocol(row, full, bound=True)
                    target = f'_cast({protocol}, {target})'
                call = target + '(' + arguments + ')'
                if tier == 'async':
                    call = 'await self.call(lambda m: ' + call + ')'
            if row.context_inplace and tier == 'context':
                lines.extend((indent + '    ' + call, indent + '    return self'))
            else:
                lines.append(indent + '    return ' + call)
            lines.append('')
        return '\n'.join(lines) + '\n'

    def imports_text(self, *, stub: bool = False, after: bool = False) -> str:
        """Publish definitions before importing higher call and annotation modules."""
        direct = [] if after else ['import builtins as _builtins', 'from typing import TYPE_CHECKING, Protocol as _Protocol, Self as _Self, cast as _cast, overload as _overload']
        if self.namespace:
            if not after:
                direct.append(f'import {self.module} as {self.namespace}')
                # The root declaration provides PEP 562 exports at runtime.
                # Its implementation needs the same typed module bindings when
                # mypy checks __init__.py independently of __init__.pyi.
                if self.imports:
                    direct.append('if TYPE_CHECKING:')
                    direct.extend(f'    import {module} as {alias}  # noqa: F401 -- accessed through the root module namespace'
                                  for module, alias in sorted(self.imports.items()))
            return '\n'.join(direct) + '\n' if direct else ''
        checked = []
        lazy = []
        internal = {module for module in self.imports if module == 'metta' or module.startswith('metta.')}
        for module, alias in sorted(self.imports.items()):
            line = f'import {module} as {alias}'
            is_direct = stub or module not in internal or binding_mode(module, self.importer) == 'direct'
            if after != (not is_direct and module not in self.early):
                continue
            if is_direct:
                direct.append(line)
            else:
                checked.append(line)
                lazy.append(f'{alias} = _lazy({module!r})')
        if not after and not stub and any(binding_mode(module, self.importer) != 'direct' for module in internal):
            direct.append('from metta._lazy import lazy as _lazy')
        result = '\n'.join(direct) + '\n' if direct else ''
        if checked:
            result += '\nif TYPE_CHECKING:\n' + ''.join('    ' + line + '\n' for line in checked)
        if lazy:
            result += 'else:\n' + ''.join('    ' + line + '\n' for line in lazy)
        return result


def header(source: str) -> str:
    """Name the declaration authority and drift check on each generated face."""
    return ('"""Purpose: expose the generated ' + source + ' door face.\n\n'
            'Generated by extensions/python/tools/doorgen.py and doorfaces.py from\n'
            'marked Python bodies and metta/_layers.py. The door-sync lane refuses\n'
            'drift; edit the declarations and regenerate this file.\n"""\n\n'
            'from __future__ import annotations\n\n')


def synchronous(rows: Iterable[Door], root: Path) -> dict[Path, str]:
    """Emit Space and MeTTa on top of their handwritten identity bases."""
    records = tuple(rows)
    result = {}
    for tier, class_name, base, module in [
        ('sync', 'Space', 'SpaceHandle', 'metta._faces.space'),
        ('context', 'MeTTa', 'MeTTaBase', 'metta._faces.metta'),
    ]:
        emitter = Emitter(root, module, '_faces')
        own = {row.python for row in records if row.owner is (Owner.space if tier == 'sync' else Owner.context) and row.body and '.' in row.body.symbol}
        selected = [row for row in records if row.owner is Owner.space and (Tier.sync if tier == 'sync' else Tier.context) in row.tiers and row.python not in own]
        methods = ''.join(emitter.method(row, tier, name=(row.alias or row.python) if tier == 'context' else row.python) for row in selected)
        namespaces = namespace_attributes(records, Tier.sync if tier == 'sync' else Tier.context)
        code = header(class_name) + emitter.imports_text()
        code += '\nfrom metta._spaces.' + ('handle' if tier == 'sync' else 'context') + ' import ' + base + '\n\n'
        if namespaces:
            code += 'import metta.doors._namespaces as _namespaces\n\n'
        code += '\n\n'.join(dict.fromkeys(emitter.protocols)) + '\n\n'
        code += f'class {class_name}({base}):\n    """The {class_name} operations declared beside their implementations."""\n\n    __slots__ = ()\n\n' + namespaces + methods
        if tier == 'sync':
            code += '    __copy__ = copy\n'
        code += '\n' + emitter.imports_text(after=True)
        path = root / 'extensions/python' / (module.replace('.', '/') + '.py')
        result[path] = clean_imports(code, path)
    return result


def namespace_attributes(rows: Iterable[Door], tier: Tier) -> str:
    """Give discovered extension namespaces their declared static interfaces."""
    from doorgen import _namespace_type  # noqa: PLC0415 -- the reader calls this emitter

    names = sorted({row.provider.namespace for row in rows
                    if row.owner is Owner.namespace and row.provider and tier in row.tiers})
    return ''.join(f'    {name}: _namespaces.{_namespace_type(name, tier)}\n' for name in names) + ('\n' if names else '')


def asynchronous(rows: Iterable[Door], root: Path) -> dict[Path, str]:
    """Emit ordinary worker calls, retaining the worker base's owned operations."""
    source = root / 'extensions/python/metta/aio/_worker.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    base = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AsyncMeTTaBase')
    own = {node.name for node in base.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    selected = [row for row in rows if row.owner in {Owner.space, Owner.namespace}
                and Tier.async_ in row.tiers and (row.alias or row.python) not in own]
    emitter = Emitter(root, 'metta.aio._mirror', 'aio')
    methods = ''.join(emitter.method(row, 'async', name=row.alias or row.python) for row in selected)
    code = header('AsyncMeTTa') + emitter.imports_text()
    code += '\nfrom metta.aio._worker import AsyncMeTTaBase\n\n'
    code += '\n\n'.join(dict.fromkeys(emitter.protocols)) + '\n\n'
    code += 'class AsyncMeTTa(AsyncMeTTaBase):\n    """The synchronous door declarations submitted to their owning worker."""\n\n' + methods
    code += '\n' + emitter.imports_text(after=True)
    path = root / 'extensions/python/metta/aio/_mirror.py'
    return {path: clean_imports(code, path)}


def module_tier(rows: Iterable[Door], root: Path, *, stub: bool = False) -> tuple[str, str]:
    """Return imports and declarations for the default context's door face."""
    emitter = Emitter(root, 'metta', 'metta', namespace='' if stub else '_root')
    selected = [row for row in rows if row.owner is Owner.space and Tier.module in row.tiers]
    methods = ''.join(emitter.method(row, 'module', name=row.alias or row.python, stub=stub) for row in selected)
    return emitter.imports_text(stub=stub), '\n\n'.join(dict.fromkeys(emitter.protocols)) + '\n\n' + methods + emitter.imports_text(stub=stub, after=True)
