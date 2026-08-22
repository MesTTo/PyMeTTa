"""Purpose: preserve the upstream ``python.petta`` package entry point.
Guarantees:
  - ``python.petta`` and ``petta`` are the same canonical module object
    [tested: test_upstream_python_package_path_is_canonical; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import sys as _sys

import petta as petta

_sys.modules[f"{__name__}.petta"] = petta

__all__ = ["petta"]
