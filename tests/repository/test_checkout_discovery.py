"""Purpose: a checkout advertises its extension distributions the way an install does.

`_workspace.on_path()` makes every member importable and adds the finder that
answers `importlib.metadata` from the members' own manifests, so entry-point
discovery, the seam's `advertised()` and every example reach a package's door
without importing the package by name.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import importlib.machinery
import sys
import tomllib
from importlib import metadata

from metta import seam

import _workspace


def _declared() -> dict[str, str]:
    """Every member's `metta.extensions` entry point, read from its manifest."""
    out: dict[str, str] = {}
    for member in _workspace.members():
        project = tomllib.loads((member / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        out.update(project.get("entry-points", {}).get(seam.GROUP, {}))
    return out


def test_a_checkout_advertises_its_members_through_importlib_metadata():
    """The checkout's members answer entry-point discovery from their manifests, with PEP 503 names."""
    names = _workspace.on_path()
    declared = _declared()
    assert declared, "the workspace declares at least one extension entry point"
    advertised = {entry.name: entry.value for entry in metadata.entry_points(group=seam.GROUP)}
    assert declared.items() <= advertised.items()
    assert names, "every member is importable, entry point target or not"
    # The seam reads the same discovery, and a loaded entry point is the module it names.
    assert declared.keys() <= seam.advertised().keys()
    name, target = next(iter(declared.items()))
    assert metadata.entry_points(group=seam.GROUP)[name].load().__name__ == target
    # Calling on_path() again adds nothing: one finder, one path entry per member.
    finders = [finder for finder in sys.meta_path if isinstance(finder, _workspace.CheckoutDistributions)]
    _workspace.on_path()
    assert [finder for finder in sys.meta_path if isinstance(finder, _workspace.CheckoutDistributions)] == finders


def test_the_manifest_outranks_a_stale_build_artefact_in_a_member(tmp_path, monkeypatch):
    """A wheel build leaves `*.egg-info` inside a member; the manifest still wins.

    The finder is first on `sys.meta_path`, and `importlib.metadata` keeps the
    first distribution per name, so the stale metadata the path finder would
    report from the member's own directory never reaches `entry_points()`.
    """
    member = tmp_path / "metta-stale"
    member.mkdir()
    (member / "pyproject.toml").write_text(
        '[project]\nname = "metta-stale"\nversion = "0.0.1"\n'
        '[project.entry-points."metta.extensions"]\nmetta-stale = "metta_stale"\n',
        encoding="utf-8",
    )
    (member / "metta_stale.py").write_text("", encoding="utf-8")
    stale = member / "metta_stale.egg-info"
    stale.mkdir()
    (stale / "PKG-INFO").write_text("Metadata-Version: 2.1\nName: metta-stale\nVersion: 0.0.0\n", encoding="utf-8")
    monkeypatch.setattr(_workspace, "EXT", tmp_path)
    monkeypatch.setattr(sys, "path", [str(member), *sys.path])
    _workspace.on_path()
    ours = next(index for index, finder in enumerate(sys.meta_path) if isinstance(finder, _workspace.CheckoutDistributions))
    path_finder = next(
        index for index, finder in enumerate(sys.meta_path)
        if finder is importlib.machinery.PathFinder or isinstance(finder, importlib.machinery.PathFinder)
    )
    assert ours < path_finder
    found = {entry.name: entry.value for entry in metadata.entry_points(group=seam.GROUP)}
    assert found["metta-stale"] == "metta_stale"
    assert metadata.version("metta-stale") == "0.0.1"
    assert metadata.version("Metta_Stale") == "0.0.1", "PEP 503 normalisation, as for an installed distribution"
