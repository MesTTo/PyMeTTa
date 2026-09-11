"""Purpose: load package exports, deferred modules and optional integrations.

Owns resources: a meta-path finder selects deferred execution for the current
thread. Importlib owns module locks and publication; _Execution unpublishes a
failed deferred module and makes retained references repeat its error
[tested: test_failed_lazy_module_cannot_publish_partial_values; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Assumes: private lazy() targets retain their ordinary module object and class.
Named exports and custom loaders use normal import_module instead.
Guarded by: importlib's module lock protects initial publication, and its
LazyLoader state lock serializes execution [source:
https://github.com/python/cpython/blob/v3.12.12/Lib/importlib/util.py#L168-L270;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Decides: packages and custom loaders execute normally; supported source modules
defer execution unless METTA_EAGER_IMPORT=1 [source:
https://github.com/python/cpython/blob/v3.12.12/Lib/importlib/util.py#L168-L302;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import collections.abc as _collections_abc
import os
import sys
from importlib import import_module

# Typeshed omits the CPython publication helper and lazy-module class.
from importlib._bootstrap import (  # type: ignore[attr-defined] # CPython 3.12+ publication helper
    _lock_unlock_module,  # ty: ignore[unresolved-import] -- CPython 3.12+ publication lock, guarded below
)
from importlib.abc import Loader
from importlib.machinery import SourceFileLoader, SourcelessFileLoader
from importlib.util import (  # type: ignore[attr-defined] # CPython 3.12+ lazy-module class
    LazyLoader,
    _LazyModule,  # ty: ignore[unresolved-import] -- CPython 3.12+ cached lazy-module identity, guarded below
)
from pkgutil import iter_modules
from threading import local
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec

if sys.implementation.name != "cpython" or sys.version_info < (3, 12):
    msg = "deferred module publication requires CPython 3.12 or later"
    raise ImportError(msg)


class _FailedModule(ModuleType):
    """A retained reference to a failed import cannot expose partial state."""

    def __getattribute__(self, name: str) -> Any:
        error = ModuleType.__getattribute__(self, "_metta_import_error")
        raise error


class _Execution(Loader):
    """Preserve ordinary failed-import cleanup behind the standard lazy loader."""

    def __init__(self, loader: SourceFileLoader | SourcelessFileLoader) -> None:
        self.loader = loader

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        """Delegate module allocation to the original standard loader."""
        return self.loader.create_module(spec)

    def __getattr__(self, name: str) -> Any:
        """Keep the original source, bytecode and resource inspection protocol."""
        return getattr(self.loader, name)

    def exec_module(self, module: ModuleType) -> None:
        """Execute once, preserving failure for held references while permitting retry."""
        spec = object.__getattribute__(module, "__spec__")
        try:
            self.loader.exec_module(module)
        except BaseException as error:
            # The stdlib lazy loader keeps is_loading set after an exception,
            # so later accesses otherwise expose the half-executed dictionary.
            # An error-reporting module follows lazy-loader's delayed-error
            # shape, with cleanup at the execution boundary:
            # https://github.com/scientific-python/lazy-loader/blob/4596986a8d276d19e2ad8713ec4fb8329d743a08/lazy_loader/__init__.py#L106-L122
            object.__setattr__(module, "_metta_import_error", error)
            object.__setattr__(module, "__class__", _FailedModule)
            if sys.modules.get(spec.name) is module:
                del sys.modules[spec.name]
            parent_name, _, child = spec.name.rpartition(".")
            parent = sys.modules.get(parent_name)
            if parent is not None:
                namespace = object.__getattribute__(parent, "__dict__")
                if namespace.get(child) is module:
                    del namespace[child]
            raise


class _DeferredFinder:
    """Let the normal import machinery acquire and release each module's lock."""

    def __init__(self) -> None:
        self.requests = local()

    def find_spec(
        self, fullname: str, path: _collections_abc.Sequence[str] | None, target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname not in getattr(self.requests, "names", ()):
            return None
        names = self.requests.names
        self.requests.names = names - {fullname}
        try:
            for finder in tuple(sys.meta_path):
                if finder is self:
                    continue
                # Distribution-only finders share sys.meta_path. CPython's
                # import search skips those without the module-finder method.
                # https://github.com/python/cpython/blob/v3.14.0/Lib/importlib/_bootstrap.py#L1243-L1294
                find_spec = getattr(finder, "find_spec", None)
                if find_spec is None:
                    continue
                spec = find_spec(fullname, path, target)
                if spec is not None:
                    if spec.submodule_search_locations is None and type(spec.loader) in (
                        SourceFileLoader, SourcelessFileLoader,
                    ):
                        spec.loader = LazyLoader(_Execution(spec.loader))
                    return spec
        finally:
            self.requests.names = names
        return None


if "_finder" not in globals():
    _finder = _DeferredFinder()
    sys.meta_path.insert(0, _finder)


def lazy(name: str) -> ModuleType:
    """Return the real module, deferring a compatible module's execution.

    Package initialization and custom module loaders retain normal import
    semantics. Named exports use ``package`` so custom module objects, including
    callable packages, keep their identity.
    """
    if os.environ.get("METTA_EAGER_IMPORT") == "1":
        return import_module(name)
    cached = sys.modules.get(name)
    if type(cached) is _LazyModule:
        # import_module reads __spec__, which executes an existing lazy module.
        # Scientific Python's load also returns the cached object directly:
        # https://github.com/scientific-python/lazy-loader/blob/4596986a8d276d19e2ad8713ec4fb8329d743a08/lazy_loader/__init__.py#L188-L194
        # Wait for importlib's publication if its loader has not returned yet.
        # The same helper accepts the partially initialized module in a cycle:
        # https://github.com/python/cpython/blob/v3.12.12/Lib/importlib/_bootstrap.py#L463-L477
        spec = object.__getattribute__(cached, "__spec__")
        if spec._initializing:
            _lock_unlock_module(name)
            cached = sys.modules.get(name)
        if cached is not None and type(cached) is _LazyModule:
            return cached
    previous: frozenset[str] = getattr(_finder.requests, "names", frozenset())
    _finder.requests.names = previous | {name}
    try:
        return import_module(name)
    finally:
        _finder.requests.names = previous


def _declared_exports(module: ModuleType) -> dict[str, tuple[str, str]]:
    """Read explicit re-exports from one package's TYPE_CHECKING declaration."""
    import ast  # noqa: PLC0415 -- only packages without generated exports parse declarations
    from importlib.util import resolve_name  # noqa: PLC0415 -- the declaration reader
    from pathlib import Path  # noqa: PLC0415 -- the declaration reader

    filename = vars(module).get('__file__')
    if not filename or Path(filename).name != '__init__.py':
        return {}
    name = module.__name__
    tree = ast.parse(Path(filename).read_text(encoding='utf-8'))
    declarations = (
        declaration
        for block in tree.body
        if isinstance(block, ast.If) and isinstance(block.test, ast.Name)
        and block.test.id == 'TYPE_CHECKING'
        for declaration in block.body if isinstance(declaration, ast.ImportFrom)
    )
    exports = {}
    for declaration in declarations:
        source = '.' * declaration.level + (declaration.module or '')
        source = resolve_name(source, name) if declaration.level else source
        # SPEC 1 distinguishes a relative child module from an attribute:
        # https://github.com/scientific-python/lazy-loader/blob/4596986a8d276d19e2ad8713ec4fb8329d743a08/lazy_loader/__init__.py#L286-L308
        child = declaration.module is None and declaration.level == 1
        for alias in declaration.names:
            if alias.asname == alias.name:
                exports[alias.name] = (f"{source}.{alias.name}", "") if child else (source, alias.name)
    return exports


def package(name: str) -> tuple[_collections_abc.Callable[[str], Any], _collections_abc.Callable[[], list[str]]]:
    """Build PEP 562 handlers from the directory and generated named exports.

    ``__lazy_exports__`` maps a public name to its module and attribute, or to
    a value factory. An empty attribute denotes the module itself. The root
    generator derives imports from the package's declaration stub.
    """
    module = sys.modules[name]
    roster = {item.name for item in iter_modules(vars(module).get('__path__', ())) if not item.name.startswith("_")}
    if '__lazy_exports__' not in vars(module):
        vars(module)['__lazy_exports__'] = _declared_exports(module)

    def getattribute(attribute: str) -> Any:
        exports = vars(module).get("__lazy_exports__", {})
        if attribute in exports:
            declaration = exports[attribute]
            if callable(declaration):
                result = declaration()
            else:
                source, member = declaration
                imported = import_module(source)
                result = getattr(imported, member) if member else imported
        elif attribute in roster:
            result = import_module(f"{name}.{attribute}")
        else:
            msg = f"module {name!r} has no attribute {attribute!r}"
            raise AttributeError(msg, name=attribute, obj=module)
        setattr(module, attribute, result)
        return result

    def directory() -> list[str]:
        exports = vars(module).get("__lazy_exports__", {})
        names = vars(module).get("__all__")
        if names is not None:
            return sorted(set(names) | roster)
        names = (key for key in vars(module) if not key.startswith("_"))
        return sorted(set(names) | roster | exports.keys())

    return getattribute, directory


def optional_module(name: str) -> ModuleType | None:
    """Import a module, returning None only when that module itself is absent."""
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name not in (name, name.partition(".")[0]):
            raise
        return None


def optional(name: str, extra: str) -> ModuleType:
    """Import an optional module or raise the caller's installation remedy."""
    module = optional_module(name)
    if module is None:
        raise ImportError(extra)
    return module
