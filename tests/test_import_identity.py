"""Purpose: pin the metta import surface and its lazy module identities.
Guarantees:
  - importing metta alone leaves optional integrations unloaded [tested
    test_optional_surfaces_load_only_when_requested]
  - the petta_ops callback facade re-exports without owning state [tested
    test_callback_facade_owns_no_state_and_delegates; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import importlib
import os
import subprocess
import sys
from pathlib import Path


def test_optional_surfaces_load_only_when_requested():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    root = Path(__file__).resolve().parents[3]
    source = """
import importlib
import sys

import metta

lazy = {'aio', 'algebra', 'arrays', 'remote', 'testing', 'wire'}
assert all(f'metta.{name}' not in sys.modules for name in lazy)
assert 'asyncio' not in sys.modules
assert 'urllib.request' not in sys.modules

for name in lazy:
    exposed = getattr(metta, name)
    assert exposed is importlib.import_module(f'metta.{name}')
assert lazy <= set(dir(metta))
"""
    environment = os.environ | {"PYTHONPATH": str(root / "bindings" / "python")}
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=environment,
        check=True,
    )


def test_callback_facade_owns_no_state_and_delegates():
    """The callback facade re-exports; it must not hold a registry itself."""
    facade = importlib.import_module("metta._callbacks")
    owners = {
        name: importlib.import_module(f"metta.{module}")
        for name, module in {
            "dispatch": "_ops",
            "dispatch_inverse": "_ops",
            "dispatch_inverse_raw": "_ops",
            "dispatch_many": "_ops",
            "dispatch_raw": "_ops",
            "dispatch_raw_many": "_ops",
            "type_names": "_ops",
            "construct_token": "_tokens",
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
            "atom_added": "events",
            "atom_removed": "events",
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
    assert set(own_state) == {"_Any", "_CALLBACKS", "_importlib", "annotations"}
    assert all(
        isinstance(owner, tuple) and len(owner) == 2
        for owner in own_state["_CALLBACKS"].values()
    )
