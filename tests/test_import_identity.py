"""Purpose: keep the upstream python.petta path on one module universe.
Guarantees:
  - both package paths resolve package and registry-bearing submodules to
    canonical petta objects [tested test_legacy_package_path_aliases_canonical_modules,
    test_legacy_path_can_be_imported_first]
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
    assert importlib.import_module("python.petta.subscribe") is canonical.subscribe


def test_legacy_path_can_be_imported_first():
    root = Path(__file__).resolve().parents[2]
    source = """
import importlib
legacy = importlib.import_module('python.petta')
canonical = importlib.import_module('petta')
assert legacy is canonical
assert importlib.import_module('python.petta.atoms') is canonical.atoms
assert importlib.import_module('python.petta.subscribe') is canonical.subscribe
"""
    environment = os.environ | {
        "PYTHONPATH": os.pathsep.join((str(root / "python"), str(root)))
    }
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=environment,
        check=True,
    )
