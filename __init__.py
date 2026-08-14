"""Purpose: preserve the legacy python.petta import as an alias of petta.
Guarantees:
  - python.petta and every public petta submodule are the canonical module
    objects [tested test_legacy_package_path_aliases_canonical_modules,
    test_legacy_path_can_be_imported_first]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import importlib
import sys

import petta as petta

sys.modules[f"{__name__}.petta"] = petta
for _lazy_name in petta._LAZY_MODULES:
    importlib.import_module(f"petta.{_lazy_name}")
for _canonical_name, _module in tuple(sys.modules.items()):
    if _canonical_name.startswith("petta."):
        sys.modules[f"{__name__}.{_canonical_name}"] = _module

__all__ = ["petta"]
