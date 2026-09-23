"""Purpose: activate the patched SWI-Prolog host a Linux wheel of pymetta carries, before janus loads.

The engine runs on a PATCHED SWI: docs/host-workarounds.md records the
defects the patches in tests/checks/host_workarounds fix, and a stock host
answers present for 14 of their reproductions and aborts the process on two
[measured 2026-09-23 on Debian's swi-prolog-nox 10.1.14]. So a manylinux wheel
of pymetta ships that host here, as package data, the way jdk4py ships a JDK:
the SWI home under `swipl/lib/swipl` and the janus bridge built against it
under `_vendor/`, with auditwheel's copies of their system libraries in
`pymetta.libs/`. The py3-none-any wheel and a checkout carry none of it, and
there `activate()` answers None and janus comes from wherever the reader
installed it.

The bridge is VENDORED under `_vendor/` rather than installed as the
top-level `janus_swi`, the way pip carries its dependencies under
`pip._vendor`. Two distributions owning one import name is last-writer-wins
on install and a broken sibling on uninstall, and a rename is not the escape:
janus names `janus_swi` in its Prolog half too, and its extension exports
`PyInit__swipl`, so the name is part of the ABI rather than a label.

This module never spells that name. What `_vendor/` holds is read from the
directory itself, so the one site naming the bridge stays
`metta._binding.runtime`, which imports it, and a vendored module added by
assemble.sh is guarded without an edit here.

Assumes: when `swipl/` is present, it and `_vendor/` were grafted by
    tools/pymetta-host/assemble.sh from ONE build, so the bridge links the
    libswipl this home belongs to.
Guarantees:
  - `activate()` answers None when this install carries no host, and
    otherwise selects the bundled bridge and home as one pair or refuses:
    a bundled bridge on a foreign home is the same ABI mismatch as a foreign
    bridge on this one [tested: extensions/python/tests/ch01_getting_started/test_host_activation.py;
    commit=WORKTREE]
  - it refuses exactly the modules `_vendor/` holds that were already
    imported from anywhere else, a module with no `__file__` included, and
    no module `_vendor/` does not hold; a home whose `_vendor/` holds
    nothing is refused as a damaged install
    [tested: extensions/python/tests/ch01_getting_started/test_host_activation.py; commit=WORKTREE]
  - it is idempotent, and it refuses BEFORE any import, because `sys.path`
    cannot undo one: `sys.modules` is consulted first, so a path inserted
    after janus loaded changes nothing
    [tested: extensions/python/tests/ch01_getting_started/test_host_activation.py; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import os
import pkgutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_VENDOR = _HERE / "_vendor"

_BUNDLED = _HERE / "swipl" / "lib" / "swipl"
#: The bundled SWI home, or None where this install carries none.
HOME: Path | None = _BUNDLED if _BUNDLED.is_dir() else None


def activate() -> Path | None:
    """Point this process at the bundled host and answer its home, or None when there is none."""
    if HOME is None:
        return None
    # pkgutil answers what a directory can be imported as, packages and
    # single modules alike, which is the question a sys.path entry poses.
    vendored = [module.name for module in pkgutil.iter_modules([str(_VENDOR)])]
    if not vendored:
        msg = (
            f"this pymetta carries a SWI home at {HOME} and no bridge under {_VENDOR}, "
            f"so the install is damaged and any janus found elsewhere would drive this home "
            f"with another build's ABI. Reinstall pymetta."
        )
        raise RuntimeError(msg)
    loaded = [sys.modules[name] for name in vendored if name in sys.modules]
    for module in loaded:
        file = getattr(module, "__file__", None)
        where = Path(file).resolve() if file else None
        if where is None or _VENDOR not in where.parents:
            name = module.__name__
            msg = (
                f"{name} was already imported from {where or 'an unknown location'}, "
                f"and it is not the copy this pymetta carries at {_VENDOR}. Driving the "
                f"bundled SWI home with another build's bridge is an ABI mismatch that "
                f"crashes later and elsewhere, so it is refused here. Import metta before "
                f"anything imports {name}, or uninstall {name} and let pymetta supply it."
            )
            raise RuntimeError(msg)
    # Checked whether or not janus has loaded: a vendored bridge that loaded
    # under a foreign SWI_HOME_DIR is the same mismatch, already in effect.
    chosen = os.environ.get("SWI_HOME_DIR")
    if chosen is not None and Path(chosen).resolve() != HOME:
        msg = (
            f"SWI_HOME_DIR names {chosen}, and this pymetta carries its own patched host "
            f"at {HOME}. The bundled bridge and home are one build, and pairing the bridge "
            f"with another home surfaces as a crash with nothing pointing back here. Unset "
            f"SWI_HOME_DIR to use the bundled host."
        )
        raise RuntimeError(msg)
    if not loaded:
        os.environ["SWI_HOME_DIR"] = str(HOME)
        vendor = str(_VENDOR)
        if vendor not in sys.path:
            sys.path.insert(0, vendor)
    return HOME
