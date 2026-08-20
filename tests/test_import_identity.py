"""Purpose: keep the upstream python.petta path on one module universe.
Guarantees:
  - both package paths resolve package and registry-bearing submodules to
    canonical petta objects [tested test_legacy_package_path_aliases_canonical_modules,
    test_legacy_path_can_be_imported_first]
  - importing petta alone leaves optional integrations unloaded [tested
    test_optional_surfaces_load_only_when_requested]
  - the petta_ops callback facade re-exports without owning state [tested
    test_callback_facade_owns_no_state_and_delegates;
    commit=7feac32972af4ad38561669eabc3c05bf1242f44]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path


def test_legacy_package_path_aliases_canonical_modules():
    canonical = importlib.import_module("petta")
    legacy = importlib.import_module("python.petta")

    assert legacy is canonical
    assert importlib.import_module("python.petta.atoms") is canonical.atoms
    assert importlib.import_module("python.petta.aio") is canonical.aio
    assert importlib.import_module("python.petta.subscribe") is canonical.subscribe


def test_legacy_path_can_be_imported_first():
    root = Path(__file__).resolve().parents[3]
    source = """
import importlib
legacy = importlib.import_module('python.petta')
canonical = importlib.import_module('petta')
assert legacy is canonical
assert importlib.import_module('python.petta.atoms') is canonical.atoms
assert importlib.import_module('python.petta.aio') is canonical.aio
assert importlib.import_module('python.petta.subscribe') is canonical.subscribe
"""
    environment = os.environ | {
        "PYTHONPATH": os.pathsep.join((str(root / "bindings" / "python"), str(root)))
    }
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=environment,
        check=True,
    )


def test_optional_surfaces_load_only_when_requested():
    root = Path(__file__).resolve().parents[3]
    source = """
import importlib
import sys

import petta

lazy = {
    'aio', 'arrays', 'das', 'persistent', 'remote', 'testing'
}
assert all(f'petta.{name}' not in sys.modules for name in lazy)
assert 'asyncio' not in sys.modules
assert 'urllib.request' not in sys.modules

for name in lazy:
    exposed = getattr(petta, name)
    assert exposed is importlib.import_module(f'petta.{name}')
assert lazy <= set(dir(petta))
"""
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=environment,
        check=True,
    )


def test_callback_facade_owns_no_state_and_delegates():
    """The petta_ops facade re-exports; it must not hold a registry itself."""
    facade = importlib.import_module("petta._callbacks")
    owners = {
        name: importlib.import_module(f"petta.{module}")
        for name, module in {
            "dispatch": "_ops",
            "dispatch_inverse": "_ops",
            "dispatch_inverse_raw": "_ops",
            "dispatch_many": "_ops",
            "dispatch_raw": "_ops",
            "dispatch_raw_many": "_ops",
            "type_names": "_ops",
            "foreign_add": "foreign",
            "foreign_add_many": "foreign",
            "foreign_atoms": "foreign",
            "foreign_clear": "foreign",
            "foreign_match": "foreign",
            "foreign_plan": "foreign",
            "foreign_pushdown": "foreign",
            "foreign_refuse": "foreign",
            "foreign_remove": "foreign",
            "foreign_transaction": "foreign",
            "is_matchable": "foreign",
            "match_object": "foreign",
            "path_begin": "paths",
            "path_step": "paths",
            "path_value": "paths",
            "atom_added": "subscribe",
            "atom_removed": "subscribe",
        }.items()
    }
    assert sorted(facade.__all__) == sorted(owners)
    owner_names = {
        "path_begin": "_path_begin",
        "path_step": "_path_step",
        "path_value": "_path_value",
    }
    for name, owner in owners.items():
        assert getattr(facade, name) is getattr(owner, owner_names.get(name, name))

    exported = set(facade.__all__)
    own_state = {
        name: value
        for name, value in vars(facade).items()
        if not name.startswith("__") and name not in exported
    }
    assert own_state == {}
