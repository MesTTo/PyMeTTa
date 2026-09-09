"""Purpose: exercise deferred import publication, failure and module identity.

Guarantees: failed imports cannot publish partial state; concurrent readers
observe one execution; custom module objects keep normal import semantics
[tested: this file; commit=WORKTREE].
Owns resources: temporary modules, finder and search path entries are removed
by fixtures after each test [source: extensions/python/tests/repository/test_lazy_loading.py:module_tree; commit=WORKTREE].
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_file_location
from pathlib import Path
from threading import Barrier, Event
from types import ModuleType, SimpleNamespace

import pytest

from metta import _lazy

SEAT = Path(__file__).resolve().parents[2]
MODULES = tuple(sorted({"metta." + str(path.relative_to(SEAT / "metta").with_suffix("")).replace(os.sep, ".")
                        .removesuffix(".__init__") for path in (SEAT / "metta").rglob("*.py")} - {"metta.__init__"}))


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("eager", ("0", "1"), ids=("deferred", "eager"))
def test_each_module_imports_first_in_a_fresh_process(module, eager):
    """No package member may rely on pytest having imported another one first."""
    program = (
        "import importlib, pathlib, sys\n"
        "module = importlib.import_module(sys.argv[1])\n"
        "assert module.__name__ == sys.argv[1]\n"
        "assert pathlib.Path(module.__spec__.origin).is_relative_to(pathlib.Path.cwd())\n"
    )
    result = subprocess.run([sys.executable, "-c", program, module], cwd=SEAT,
                            env=os.environ | {"METTA_EAGER_IMPORT": eager}, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def module_tree(tmp_path, monkeypatch):
    """Keep probe modules out of the real package and restore import state."""
    monkeypatch.delenv("METTA_EAGER_IMPORT", raising=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    directory = tmp_path / "layout_import_probe"
    directory.mkdir()
    (directory / "__init__.py").write_text("")
    try:
        yield directory
    finally:
        for name in tuple(sys.modules):
            if name == "layout_import_probe" or name.startswith("layout_import_probe."):
                del sys.modules[name]
        importlib.invalidate_caches()


def test_real_module_is_deferred_once_and_shared(module_tree):
    """Import returns the registered module without executing its source."""
    (module_tree / "body.py").write_text("value = object()\n")
    body = _lazy.lazy("layout_import_probe.body")
    assert "value" not in object.__getattribute__(body, "__dict__")
    assert sys.modules["layout_import_probe.body"] is body
    assert _lazy.lazy("layout_import_probe.body") is body
    assert "value" not in object.__getattribute__(body, "__dict__")
    importlib.reload(_lazy)
    assert _lazy.lazy("layout_import_probe.body") is body
    assert "value" not in object.__getattribute__(body, "__dict__")
    value = body.value
    assert importlib.import_module("layout_import_probe.body") is body
    assert body.value is value


@pytest.mark.parametrize("fails", [False, True])
def test_concurrent_readers_share_execution_and_failure(module_tree, fails):
    """Two first readers cannot observe state before source execution ends."""
    started, release, readers = Event(), Event(), Barrier(3)
    parent = importlib.import_module("layout_import_probe")
    parent.control = SimpleNamespace(started=started, release=release, calls=[])
    source = (
        "from layout_import_probe import control\n"
        "control.calls.append(1)\n"
        "partial = 23\n"
        "control.started.set()\n"
        "control.release.wait()\n"
    )
    if fails:
        source += 'raise RuntimeError("broken body")\n'
    (module_tree / "body.py").write_text(source)
    body = _lazy.lazy("layout_import_probe.body")

    def read():
        readers.wait()
        return body.partial

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(read) for _ in range(2)]
        try:
            readers.wait()
            started.wait()
            assert all(not future.done() for future in pending)
        finally:
            release.set()
        if fails:
            for future in pending:
                with pytest.raises(RuntimeError, match="broken body"):
                    future.result()
        else:
            assert [future.result() for future in pending] == [23, 23]
    assert parent.control.calls == [1]


def test_failed_lazy_module_cannot_publish_partial_values(module_tree):
    """Held references repeat failure while a repaired module can be imported."""
    path = module_tree / "body.py"
    path.write_text('partial = 23\nraise RuntimeError("broken body")\n')
    parent = importlib.import_module("layout_import_probe")
    body = _lazy.lazy("layout_import_probe.body")
    for _ in range(2):
        with pytest.raises(RuntimeError, match="broken body"):
            _ = body.partial
    assert "layout_import_probe.body" not in sys.modules
    assert "body" not in vars(parent)
    path.write_text("partial = 999\n")
    importlib.invalidate_caches()
    repaired = _lazy.lazy("layout_import_probe.body")
    assert repaired is not body
    assert repaired.partial == 999
    with pytest.raises(RuntimeError, match="broken body"):
        _ = body.partial


def test_eager_import_refuses_at_the_call(module_tree, monkeypatch):
    """The suite's switch uses ordinary immediate import failure cleanup."""
    monkeypatch.setenv("METTA_EAGER_IMPORT", "1")
    (module_tree / "body.py").write_text('raise RuntimeError("eager body")\n')
    with pytest.raises(RuntimeError, match="eager body"):
        _lazy.lazy("layout_import_probe.body")
    assert "layout_import_probe.body" not in sys.modules


def test_custom_source_loader_keeps_callable_module_identity(module_tree, monkeypatch):
    """A custom loader is not eligible for the whole-module lazy mechanism."""
    path = module_tree / "body.py"
    path.write_text("value = 42\n")

    class CallableModule(ModuleType):
        def __call__(self):
            return self.value

    class Loader(SourceFileLoader):
        def create_module(self, spec):
            return CallableModule(spec.name)

    class Finder:
        def find_spec(self, fullname, path=None, target=None):
            del path, target
            if fullname == "layout_import_probe.body":
                return spec_from_file_location(fullname, source, loader=Loader(fullname, str(source)))
            return None

    source = path
    monkeypatch.setattr(sys, "meta_path", [Finder(), *sys.meta_path])
    body = _lazy.lazy("layout_import_probe.body")
    assert isinstance(body, CallableModule)
    assert body() == 42
    assert importlib.import_module("layout_import_probe.body") is body


def test_named_exports_preserve_custom_module_objects(module_tree):
    """PEP 562 resolves names and callable source modules through normal import."""
    (module_tree / "__init__.py").write_text(
        "from metta._lazy import package\n"
        '__lazy_exports__ = {"named": ("layout_import_probe.body", ""), '
        '"answer": ("layout_import_probe.body", "value")}\n'
        "__getattr__, __dir__ = package(__name__)\n"
    )
    (module_tree / "body.py").write_text(
        "import sys\nfrom types import ModuleType\n"
        "class CallableModule(ModuleType):\n"
        "    def __call__(self):\n        return self.value\n"
        "value = 42\nsys.modules[__name__].__class__ = CallableModule\n"
    )
    parent = importlib.import_module("layout_import_probe")
    assert {"body", "named", "answer"} <= set(dir(parent))
    assert "layout_import_probe.body" not in sys.modules
    assert parent.named is importlib.import_module("layout_import_probe.body")
    assert parent.named() == parent.answer == 42


@pytest.mark.parametrize("eager", ("0", "1"))
def test_explicit_child_modules_and_private_exports_wait_for_access(module_tree, monkeypatch, eager):
    """Explicit relative module exports keep Python module and value identity."""
    monkeypatch.setenv("METTA_EAGER_IMPORT", eager)
    (module_tree / "__init__.py").write_text(
        "from typing import TYPE_CHECKING\nfrom metta._lazy import package\n"
        "if TYPE_CHECKING:\n"
        "    from . import body as body\n"
        "    from . import _hidden as _hidden\n"
        "    from .body import _value as _value\n"
        "__getattr__, __dir__ = package(__name__)\n"
    )
    (module_tree / "body.py").write_text("_value = object()\n")
    (module_tree / "_hidden.py").write_text("value = object()\n")
    parent = importlib.import_module("layout_import_probe")
    assert {"body", "_hidden", "_value"} <= set(dir(parent))
    assert "layout_import_probe.body" not in sys.modules
    assert "layout_import_probe._hidden" not in sys.modules
    assert parent.body is importlib.import_module("layout_import_probe.body")
    assert parent._value is parent.body._value
    assert parent._hidden is importlib.import_module("layout_import_probe._hidden")


def test_optional_remedy_does_not_mask_a_transitive_missing_import(module_tree):
    """Only absence of the requested module receives the caller's remedy."""
    with pytest.raises(ImportError, match="install the probe extra"):
        _lazy.optional("layout_import_probe.missing", "install the probe extra")
    (module_tree / "body.py").write_text("import layout_missing_dependency\n")
    with pytest.raises(ModuleNotFoundError) as refused:
        _lazy.optional("layout_import_probe.body", "install the probe extra")
    assert refused.value.name == "layout_missing_dependency"


def test_helper_reload_keeps_one_finder():
    """Reload cannot accumulate a finder or lose its thread-local requests."""
    finder = _lazy._finder
    importlib.reload(_lazy)
    assert _lazy._finder is finder
    assert sum(item is finder for item in sys.meta_path) == 1
