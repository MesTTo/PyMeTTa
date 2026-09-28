"""Purpose: generate root exports and door faces from the package declaration.

The declaration-to-runtime direction follows Scientific Python SPEC 1:
https://scientific-python.org/specs/spec-0001/. Named imports identify their
implementations; the directory identifies satellites. Callable module types
remain declarations in the stub and keep their real runtime module objects.

Guarantees: init-stub compares the runtime root, catalog carrier declaration,
door declarations and algebra consumer against these authorities [tested:
init-stub; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
__all__, in the declaration and the runtime alike, is every explicit
re-export and every module door, derived rather than listed [tested 2026-09-25T23:30:47+10:00:
test_all_is_every_public_name_the_root_resolves,
test_root_exports_and_new_carrier_reach_runtime_and_consumer].
probe_text checks exact root and callable-algebra result types;
Any and a non-callable module are independently rejected [tested:
test_root_consumer_rejects_any_and_non_callable_exports; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
The `algebra` declaration is the module's runtime class: each name in
metta.algebra's `__all__` bound to the module's own object, and the call as
the class's own overloads, so a checker reads metta.algebra.X exactly where
`from metta.algebra import X` reads it [tested 2026-09-29T02:54:59+10:00:
test_root_exports_and_new_carrier_reach_runtime_and_consumer,
test_the_algebra_declaration_is_the_module_s_own_surface; mypy-algebra-surface].
Fails when: metta.algebra exports an overloaded function or a name no
module-level definition or import binds, which it refuses by name: a static
binding of an overloaded function keeps only its first overload.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import copy
import sys
import textwrap
from collections.abc import Iterable
from importlib.util import resolve_name
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = next(parent for parent in TOOLS.parents
            if (parent / "engine").is_dir() and (parent / "lib").is_dir())
# Repo-RELATIVE, because each of these four facts is needed twice over: once
# here against this checkout, and once inside projections/2 against whatever
# `root` it is handed, which is how the mutation lanes run it over a temporary
# tree. Fixed to ROOT they cannot serve the second caller, which is why
# `__init__.pyi` had come to be written out four times and the type probe's
# path three, while the two ROOT-fixed names nothing could use read as dead.
CORE_PATH = 'extensions/python/metta'
SOURCE_NAME = '__init__.py'
STUB_NAME = '__init__.pyi'
PROBE_PATH = 'extensions/python/tests/typing/algebra_surface.py'
CORE = ROOT / CORE_PATH
SOURCE = CORE / SOURCE_NAME
sys.path[:0] = [str(TOOLS), str(ROOT / 'extensions/python')]

from artifacts import notice  # noqa: E402 -- the checkout path precedes tool imports
from doorfaces import (  # noqa: E402 -- the checkout path precedes tool imports
    Emitter,
    _bindings,
    clean_imports,
    header,
    module_doors,
    module_tier,
)
from doorgen import (  # noqa: E402 -- the checkout path precedes tool imports
    all_rows,
    module_path,
    replace_region,
    signature_lines,
)
from vocabgen import member_name  # noqa: E402 -- the checkout path precedes tool imports

from metta import vocabularies  # noqa: E402 -- read the checkout's vocabulary
from metta.doors import Signature  # noqa: E402 -- read the checkout's door schema

ALGEBRA = 'metta.algebra'

PROBE_HEADER = ('"""Purpose: type-check root exports and callable algebra carriers.\n\n'
                + textwrap.fill(notice(PROBE_PATH), width=78)
                + '\nCheck with `sh check.sh init-stub mypy`.\n"""\n')


def _carrier_names(rows: list[tuple[str, list[str]]]) -> list[str]:
    """Return the single semiring vocabulary as safe Python attributes."""
    matches = [values for name, values in rows if name == "semiring"]
    if len(matches) != 1 or not matches[0]:
        msg = "the catalog must expose exactly one non-empty (vocabulary semiring ...) row"
        raise SystemExit(msg)
    names = [member_name(value) for value in matches[0]]
    if len(names) != len(set(names)):
        msg = "semiring vocabulary values collide as Python carrier attributes"
        raise SystemExit(msg)
    return names


def _decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    return target.attr if isinstance(target, ast.Attribute) else getattr(target, 'id', '')


def _overloaded(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_decorator_name(decorator) == 'overload' for decorator in node.decorator_list)


def _definitions(module: str, root: Path) -> tuple[ast.Module, dict[str, str]]:
    """A module's syntax tree and the kind of each name it defines at top level.

    The kind decides the stub binding: a `class` is aliased, a `function`
    aliased through staticmethod so the declaring class does not bind it as a
    method, a `value` aliased, and an `overloaded` function refused.
    """
    tree = ast.parse(module_path(module, root).read_text(encoding='utf-8'))
    kinds: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            kinds[node.name] = 'class'
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kinds[node.name] = 'overloaded' if _overloaded(node) or kinds.get(node.name) == 'overloaded' else 'function'
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            kinds[node.target.id] = 'value'
        elif isinstance(node, ast.Assign):
            kinds.update((target.id, 'value') for target in node.targets if isinstance(target, ast.Name))
    return tree, kinds


def _kind(module: str, name: str, root: Path) -> str:
    """What `name` is where it is defined, following the module's own imports."""
    _, kinds = _definitions(module, root)
    if name in kinds:
        return kinds[name]
    source, member = _bindings(module, root).get(name, (None, None))
    if source is None or member is None or not source.startswith('metta.'):
        message = f'{module}.{name} is exported and no definition or metta import binds it'
        raise SystemExit(message)
    return _kind(source, member, root)


def algebra_surface(root: Path = ROOT) -> tuple[list[str], dict[str, str], list[ast.FunctionDef]]:
    """metta.algebra's `__all__`, each name's kind, and its class's call overloads."""
    tree, _ = _definitions(ALGEBRA, root)
    exported = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == '__all__' for target in node.targets))
    kinds = {name: _kind(ALGEBRA, name, root) for name in exported}
    overloaded = sorted(name for name, kind in kinds.items() if kind == 'overloaded')
    if overloaded:
        message = (f'{ALGEBRA} exports overloaded functions {", ".join(overloaded)}; a static '
                   'staticmethod binding keeps only the first overload, so declare them another way')
        raise SystemExit(message)
    module_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == '_AlgebraModule')
    calls = [node for node in module_class.body
             if isinstance(node, ast.FunctionDef) and node.name == '__call__' and _overloaded(node)]
    if not calls:
        message = f'{ALGEBRA}._AlgebraModule declares no __call__ overloads for the stub to copy'
        raise SystemExit(message)
    return exported, kinds, calls


def _algebra_module(emitter: Emitter, surface: tuple[list[str], dict[str, str], list[ast.FunctionDef]]) -> str:
    """Declare `algebra` as an instance of the module's runtime class.

    The runtime replaces the module object's class with one that has
    `__call__`, which no checker models, so the stub declares the attribute
    as that class. Its body is the module's own surface: every `__all__` name
    bound to the module's object and the call as the class's own overloads,
    both read from the source, so neither is a second list to keep in step.
    """
    exported, kinds, calls = surface
    lines = [f'class _AlgebraModule({emitter.qualified(("types", "ModuleType"))}):']
    for name in exported:
        target = emitter.qualified((ALGEBRA, name))
        lines.append(f'    {name} = _builtins.staticmethod({target})' if kinds[name] == 'function'
                     else f'    {name} = {target}')
    for call in calls:
        args = copy.deepcopy(call.args)
        for parameter in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
            parameter.annotation = emitter.expression(parameter.annotation, ALGEBRA)
        args.defaults = [ast.Constant(Ellipsis) for _ in args.defaults]
        args.kw_defaults = [None if value is None else ast.Constant(Ellipsis) for value in args.kw_defaults]
        returns = emitter.expression(call.returns, ALGEBRA)
        signature = Signature(parameters=ast.unparse(args),
                              returns=ast.unparse(returns) if returns is not None else None,
                              declarations=('overload',))
        lines.extend(('', '    @_overload', *signature_lines(signature, '__call__'), '        ...'))
    return '\n'.join(lines) + '\n\n\nalgebra: _AlgebraModule\n'


def probe_text(carriers: list[str], rooted: set[str], exported: list[str], kinds: dict[str, str]) -> str:
    """Render the static consumer that exercises both calls, every carrier and every export."""
    attributes = "\n".join(
        (
            f"assert_type(metta.algebra.{name}, DeclaredAlgebra)\n"
            f"assert_type(metta.{name}, DeclaredAlgebra)"
            if name in rooted
            else f"assert_type(metta.algebra.{name}, DeclaredAlgebra)"
        )
        for name in carriers
    )
    classes = [name for name in exported if kinds.get(name) == 'class']
    functions = [name for name in exported if kinds.get(name) == 'function']
    imported = ", ".join(sorted({*classes, "DeclaredAlgebra"}))
    members = "\n".join(f"assert_type(metta.algebra.{name}, type[{name}])" for name in classes)
    called = "".join(f"\n    metta.algebra.{name}," for name in functions)
    return f"""{PROBE_HEADER}
from collections.abc import Callable
from types import ModuleType
from typing import assert_type

import metta
from metta._atoms.factories import Atom, Symbol
from metta._atoms.namespace import _Namespace
from metta.algebra import {imported}

assert_type(metta.S, _Namespace[Symbol])
assert_type(metta.fn.car_atom, Symbol)
assert_type(metta.convert, ModuleType)
assert_type(metta.forms("(x)"), list[Atom])
assert_type(metta.run("!(x)"), list[list[Atom]])
assert_type(metta.algebra(int), DeclaredAlgebra)
assert_type(metta.algebra(), Callable[[type], DeclaredAlgebra])
assert_type(
    metta.algebra(
        "typed-int-product", plus=max, times=lambda a, b: a * b,
        zero=0, one=1, type=int,
    ),
    DeclaredAlgebra,
)
assert_type(metta.algebra(type=int), Callable[[type], DeclaredAlgebra])
assert_type(metta.algebra(int, negate="neg", saturated="sat", variable="var"), DeclaredAlgebra)
assert_type(metta.algebra.__name__, str)
{attributes}
{members}

_functions = ({called}
)

_not_an_integer: int = metta.algebra(int)  # type: ignore[assignment]
"""


def published(declaration: str, doors: Iterable[str]) -> list[str]:
    """Name what the root publishes: each explicit re-export and each module door.

    `from m import X as X` is a stub's explicit re-export
    [source 2026-09-25T23:37:13+10:00: the typing spec's Import Conventions,
    https://github.com/python/typing/blob/0fed553b30cbbcc9d963aeb606a52fd44e8d9c35/docs/spec/distributing.rst#L404-L414],
    the form every public root name is imported in and no private alias takes,
    and the doors are the functions module_tier() writes into the root. Both
    are read rather than listed, so a name the root resolves cannot be left
    out of __all__ the way formula, polynomial and visibility were.
    """
    reexported = {alias.name for node in ast.parse(declaration).body
                  if isinstance(node, (ast.Import, ast.ImportFrom))
                  for alias in node.names if alias.asname == alias.name}
    return sorted(reexported | set(doors))


def exports(source: str) -> tuple[list[str], dict[str, tuple[str, str]]]:
    """Resolve the declaration's explicit named imports, refusing missing exports."""
    tree = ast.parse(source)
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == '__all__' for target in node.targets)]
    if len(assignments) != 1:
        message = 'the root declaration needs exactly one literal __all__'
        raise ValueError(message)
    names = ast.literal_eval(assignments[0].value)
    if not isinstance(names, list) or any(not isinstance(name, str) or not name.isidentifier() for name in names) or len(set(names)) != len(names):
        message = 'root exports must be unique Python identifiers'
        raise ValueError(message)
    imported = {}
    functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.partition('.')[0]] = (alias.name, '')
        elif isinstance(node, ast.ImportFrom):
            module = '.' * node.level + (node.module or '')
            if node.level:
                module = resolve_name(module, 'metta')
            for alias in node.names:
                name = alias.asname or alias.name
                if name in names:
                    imported[name] = (module, alias.name)
    missing = set(names) - imported.keys() - functions
    if missing:
        raise ValueError('root exports lack declarations: ' + ', '.join(sorted(missing)))
    return names, imported


def projections(rows=None, root: Path = ROOT) -> dict[Path, str]:
    """Derive the runtime, marked declarations and executable carrier consumer."""
    if rows is None:
        rows = all_rows(root)
    core = root / CORE_PATH
    declaration = (core / STUB_NAME).read_text(encoding='utf-8')
    carriers = _carrier_names([('semiring', [str(value) for value in vocabularies.Semiring])])
    emitter = Emitter(root, 'metta', 'metta')
    surface = algebra_surface(root)
    algebra = _algebra_module(emitter, surface)
    imports, methods = module_tier(rows, root, stub=True, emitter=emitter)
    for start, end, content in (
        ('# begin generated root imports', '# end generated root imports', imports),
        ('# begin generated root declarations', '# end generated root declarations', methods),
        ('# begin generated algebra declaration', '# end generated algebra declaration', algebra),
    ):
        declaration = replace_region(declaration, start, end, [start, *content.splitlines(), end])
    start, end = '# begin generated root exports', '# end generated root exports'
    names = published(declaration, (name for name, _ in module_doors(rows)))
    declaration = replace_region(declaration, start, end, [start, f'__all__ = {names!r}', end])
    declaration = clean_imports(declaration, core / STUB_NAME)
    names, imported = exports(declaration)
    table = '\n'.join(f'    {name!r}: {value!r},' for name, value in sorted(imported.items()))
    exported = '\n'.join(f'    {name!r},' for name in names)
    runtime = header('root', f'{CORE_PATH}/{SOURCE_NAME}')
    runtime += 'from metta._lazy import package as _package\n'
    runtime += 'from metta._spaces.ambient import engine as engine\n\n'
    imports, methods = module_tier(rows, root)
    runtime += imports + '\n'
    typed_exports = [f'    from {module} import {member} as {name}'
                     + ('  # noqa: A004 -- the declared public spelling' if name in vars(builtins) else '')
                     for name, (module, member) in sorted(imported.items()) if member and name != 'engine']
    if typed_exports:
        runtime += 'if TYPE_CHECKING:\n' + '\n'.join(typed_exports) + '\n\n'
    runtime += '__all__ = [\n' + exported + '\n]\n\n'
    runtime += '__lazy_exports__ = {\n' + table + '\n}\n\n'
    runtime += '__getattr__, __dir__ = _package(__name__)\n\n'
    runtime += '# begin generated module tier\n' + methods + '# end generated module tier\n'
    return {
        core / STUB_NAME: declaration,
        core / SOURCE_NAME: clean_imports(runtime, core / SOURCE_NAME),
        root / PROBE_PATH: clean_imports(probe_text(carriers, set(imported) & set(carriers), *surface[:2]),
                                          root / PROBE_PATH),
    }


def main(argv: list[str] | None = None) -> int:
    """Check the projections, or regenerate them from the declarations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    stale = []
    for path, wanted in projections().items():
        if path.is_file() and path.read_text(encoding='utf-8') == wanted:
            continue
        if args.write:
            path.write_text(wanted, encoding='utf-8')
            print('wrote ' + str(path.relative_to(ROOT)))
        else:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print('init-stub: stale projections: ' + ', '.join(stale))
        return 1
    print('init-stub: root declarations, runtime exports and carrier consumer agree')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
