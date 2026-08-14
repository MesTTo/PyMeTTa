"""Purpose: preserve the legacy python.petta import as an alias of petta.
Guarantees:
  - python.petta and each already-loaded petta submodule are the canonical
    module objects [tested test_legacy_package_path_aliases_canonical_modules]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import sys

import petta as petta

sys.modules[f"{__name__}.petta"] = petta
for _canonical_name, _module in tuple(sys.modules.items()):
    if _canonical_name.startswith("petta."):
        sys.modules[f"{__name__}.{_canonical_name}"] = _module

__all__ = ["petta"]
