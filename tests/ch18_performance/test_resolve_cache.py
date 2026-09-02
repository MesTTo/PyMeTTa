"""Purpose: keep repeated Python-name resolution out of the import machinery.

Guarantees:
  - after one successful lookup, repeated lookups make no prefix imports while
    still reading final attributes live [tested:
    test_repeated_resolution_reuses_the_import_plan,
    test_resolution_reuses_the_prefix_and_reads_the_current_attribute;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - replacement modules and newly loaded longer prefixes supersede cached
    plans [tested: test_resolution_refreshes_after_module_replacement,
    test_resolution_refreshes_when_a_longer_module_is_loaded,
    test_a_failed_final_read_does_not_poison_a_later_lookup;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - cached plans neither own temporary modules nor grow beyond the fixed bound
    [tested: test_resolution_plans_do_not_own_temporary_modules,
    test_resolution_plan_cache_is_bounded;
    commit=d0bb2ff730a491eac9a0c679a4e2abe0f93ab196]
  - a candidate module's internal ImportError or missing dependency propagates
    unchanged instead of being mistaken for an absent candidate [tested:
    test_resolution_preserves_internal_failure_from_an_importable_prefix;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import gc
import sys
import types
import weakref
from typing import Any

import pytest

import metta_py


def _clear_cache() -> None:
    metta_py.clear_resolve_cache()


def test_repeated_resolution_reuses_the_import_plan(monkeypatch):
    """A hot name performs attribute reads and no repeated prefix imports."""
    _clear_cache()
    expected = metta_py.resolve("os.path.join")
    imported: list[str] = []
    original = metta_py.importlib.import_module

    def counted(name: str):
        imported.append(name)
        return original(name)

    monkeypatch.setattr(metta_py.importlib, "import_module", counted)
    for _ in range(64):
        assert metta_py.resolve("os.path.join") is expected

    assert imported == []


def test_resolution_reuses_the_prefix_and_reads_the_current_attribute(monkeypatch):
    """The cached prefix is a plan, not a stale final object."""
    _clear_cache()
    name = "p25_live_resolution"
    module: Any = types.ModuleType(name)
    first, second = object(), object()
    module.value = first
    monkeypatch.setitem(sys.modules, name, module)

    assert metta_py.resolve(f"{name}.value") is first
    module.value = second
    assert metta_py.resolve(f"{name}.value") is second


def test_resolution_refreshes_after_module_replacement(monkeypatch):
    """Replacing a sys.modules binding invalidates its earlier plan."""
    _clear_cache()
    name = "p25_replaced_resolution"
    first: Any = types.ModuleType(name)
    second: Any = types.ModuleType(name)
    first_value, second_value = object(), object()
    first.value = first_value
    second.value = second_value
    monkeypatch.setitem(sys.modules, name, first)

    assert metta_py.resolve(f"{name}.value") is first_value
    monkeypatch.setitem(sys.modules, name, second)
    assert metta_py.resolve(f"{name}.value") is second_value


def test_resolution_refreshes_when_a_longer_module_is_loaded(monkeypatch):
    """A newly loaded child module outranks an older attribute fallback."""
    _clear_cache()
    package_name = "p25_resolution_package"
    child_name = f"{package_name}.child"
    package: Any = types.ModuleType(package_name)
    package.__path__ = []
    old_value, new_value = object(), object()
    package.child = types.SimpleNamespace(value=old_value)
    child: Any = types.ModuleType(child_name)
    child.value = new_value
    monkeypatch.setitem(sys.modules, package_name, package)

    assert metta_py.resolve(f"{child_name}.value") is old_value
    monkeypatch.setitem(sys.modules, child_name, child)
    assert metta_py.resolve(f"{child_name}.value") is new_value


def test_a_failed_final_read_does_not_poison_a_later_lookup(monkeypatch):
    """A later attribute assignment can repair an earlier missing name."""
    _clear_cache()
    name = "p25_repaired_resolution"
    module: Any = types.ModuleType(name)
    monkeypatch.setitem(sys.modules, name, module)

    with pytest.raises(AttributeError, match="has no attribute 'value'"):
        metta_py.resolve(f"{name}.value")

    expected = object()
    module.value = expected
    assert metta_py.resolve(f"{name}.value") is expected


@pytest.mark.parametrize("failure_kind", ["missing-dependency", "from-list"])
def test_resolution_preserves_internal_failure_from_an_importable_prefix(
    monkeypatch,
    failure_kind,
):
    """P32: only the attempted candidate's absence permits prefix fallback."""
    _clear_cache()
    module_name = "p32_broken_resolution"
    path = f"{module_name}.value"
    failure: ImportError
    if failure_kind == "missing-dependency":
        failure = ModuleNotFoundError(name="p32_internal_dependency", path=None)
    else:
        failure = ImportError("cannot import name 'required_value'")
    attempted = []

    def broken_import(name: str):
        attempted.append(name)
        if name == path:
            raise ModuleNotFoundError(name=path, path=None)
        if name == module_name:
            raise failure
        msg = f"unexpected import candidate {name!r}"
        raise AssertionError(msg)

    monkeypatch.setattr(metta_py.importlib, "import_module", broken_import)
    with pytest.raises(type(failure)) as caught:
        metta_py.resolve(path)
    assert caught.value is failure
    assert attempted == [path, module_name]
    _clear_cache()


def test_resolution_plans_do_not_own_temporary_modules():
    """Removing the import registry's reference lets a cached module die."""
    _clear_cache()
    name = "p25_temporary_resolution"
    assert name not in sys.modules
    module = types.ModuleType(name)
    reference = weakref.ref(module)
    sys.modules[name] = module
    try:
        assert metta_py.resolve(name) is module
    finally:
        sys.modules.pop(name, None)
        del module
    gc.collect()

    assert reference() is None
    _clear_cache()


def test_resolution_plan_cache_is_bounded(monkeypatch):
    """Distinct successful paths cannot make the process cache unbounded."""
    _clear_cache()
    maximum = metta_py.RESOLVE_CACHE_MAX
    for index in range(maximum + 64):
        name = f"p25_bounded_resolution_{index}"
        module = types.ModuleType(name)
        monkeypatch.setitem(sys.modules, name, module)
        assert metta_py.resolve(name) is module

    info = metta_py._resolve_plan.cache_info()
    assert info.maxsize == maximum
    assert info.currsize == maximum
    _clear_cache()
