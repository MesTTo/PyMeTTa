"""Purpose: reach this repository's extension distributions from a checkout.

Each `ext/metta-<name>/` is its own distribution and a checkout is not an
install, so nothing has written a `dist-info` and neither `import metta_pandas`
nor entry-point discovery works without help. This puts each member's directory
on `sys.path`, which is what lets the suite and the benchmark drivers import a
member and let its module body register its rows. The ENTRY-POINT half is
proved where it can be proved honestly, by the shell proofs that build and
install a distribution for real.

Derived from the directory rather than a list, so a package added under `ext/`
needs no edit anywhere.

Assumes: every member's module sits directly in its distribution directory,
  which `tests/checks/check_layering.py` holds it to.
Guarantees:
  - `on_path()` is idempotent and answers the module names it made reachable
    [tested: tests/checks/check_layering_selftest.py; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sys
from pathlib import Path

EXT = Path(__file__).resolve().parent / "ext"


def members() -> list[Path]:
    """Every extension distribution's directory, in name order."""
    return sorted(path for path in EXT.glob("metta-*") if path.is_dir())


def module_names() -> list[str]:
    """The module each distribution ships, `metta-pandas` giving metta_pandas."""
    return [path.name.replace("-", "_") for path in members()]


def on_path() -> list[str]:
    """Make every member importable, answering their module names."""
    for member in members():
        location = str(member)
        if location not in sys.path:
            sys.path.insert(0, location)
    return module_names()
