"""Purpose: reach this repository's extension distributions from a checkout.

Each `ext/metta-<name>/` is its own distribution and a checkout is not an
install, so nothing has written a `dist-info`: neither `import metta_pandas`
nor entry-point discovery works without help. `on_path()` puts each member's
directory on `sys.path` and adds one distribution finder to `sys.meta_path`
that answers `importlib.metadata` from the members' own `pyproject.toml`
files, so `entry_points(group="metta.extensions")` lists a checkout's members
the way it lists installed ones and the seam discovers them the same way.
The finder goes first on `sys.meta_path`, as the members go first on
`sys.path`, so metadata and imports name the same checkout; `importlib.metadata`
keeps one distribution per name, the first found [source:
https://docs.python.org/3/library/importlib.metadata.html#implementing-custom-providers].

Derived from the directory rather than a list, so a package added under `ext/`
needs no edit anywhere.

Assumes: every member's module sits directly in its distribution directory and
  its `pyproject.toml` carries `[project]` with its entry points, which
  `tests/checks/check_layering.py` holds it to.
Guarantees:
  - `on_path()` is idempotent and answers the module names it made reachable
    [tested: tests/checks/check_layering_selftest.py; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - after `on_path()`, `importlib.metadata.entry_points(group="metta.extensions")`
    names every member and each entry point loads its module [tested:
    test_a_checkout_advertises_its_members_through_importlib_metadata;
    commit=58bf75947fc58ec32b2372ef0d2c14a00aa2390a]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import re
import sys
import tomllib
from collections.abc import Iterator
from importlib import metadata
from pathlib import Path

#: The one level count in the tree. A count is silent when it is wrong -- the
#: glob matches nothing and every member stops being importable with no error
#: naming the cause -- so it is made once here and named everywhere else, and
#: `tests/checks/check_layering.py` compares EXT against the workspace roster
#: so a layout change fails a lane instead of a member's imports
#: [measured 2026-09-19: the move to a top-level `ext/` left five files
#: counting to the old depth, costing 22 collection errors and 12 setup
#: errors before the count became one].
#: The distributions are a sibling of `extensions/`, not of this file: they
#: are a separate component so that deleting `ext/` leaves the seat whole,
#: which it cannot be while they sit inside it.
SEAT = Path(__file__).resolve().parent
ROOT = SEAT.parents[1]
EXT = ROOT / "ext"


def members() -> list[Path]:
    """Every extension distribution's directory, in name order."""
    return sorted(path for path in EXT.glob("metta-*") if path.is_dir())


def module_names() -> list[str]:
    """The module each distribution ships, `metta-pandas` giving metta_pandas."""
    return [path.name.replace("-", "_") for path in members()]


class CheckoutDistribution(metadata.Distribution):
    """One member's metadata, read from its `pyproject.toml` instead of a dist-info."""

    def __init__(self, member: Path) -> None:
        self._member = member
        self._project = tomllib.loads((member / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    def read_text(self, filename: str) -> str | None:
        """Answer the two files `importlib.metadata` reads, rendered from the manifest."""
        if filename == "METADATA":
            return (
                "Metadata-Version: 2.1\n"
                f"Name: {self._project['name']}\n"
                f"Version: {self._project.get('version', '0')}\n"
            )
        if filename == "entry_points.txt":
            return "".join(
                f"[{group}]\n" + "".join(f"{name} = {target}\n" for name, target in targets.items())
                for group, targets in self._project.get("entry-points", {}).items()
            )
        return None

    def locate_file(self, path: str | Path) -> Path:
        """A member's files are its directory's."""
        return self._member / path


class CheckoutDistributions(metadata.DistributionFinder):
    """The finder that makes a checkout's members visible to `importlib.metadata`.

    It finds no modules (`sys.path` carries the members already), only their
    metadata, and it goes FIRST on `sys.meta_path` for the same reason the
    members go first on `sys.path`: what `import metta_live` resolves to and
    what `importlib.metadata` says about `metta-live` must be the same
    checkout. `importlib.metadata` keeps the first distribution per name, so
    a stale `*.egg-info` a wheel build left inside a member directory, which
    the path finder would otherwise report ahead of the manifest, never wins.
    """

    def find_distributions(
        self, context: metadata.DistributionFinder.Context | None = None
    ) -> Iterator[metadata.Distribution]:
        """Every member, or the one `context.name` asks for, by normalised name."""
        wanted = None if context is None or context.name is None else _normalised(context.name)
        for member in members():
            if wanted is None or wanted == _normalised(member.name):
                yield CheckoutDistribution(member)


def _normalised(name: str) -> str:
    """PEP 503's project-name normalisation: `metta_live`, `Metta-Live` and `metta-live` are one name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def on_path() -> list[str]:
    """Make every member importable and discoverable, answering their module names."""
    for member in members():
        location = str(member)
        if location not in sys.path:
            sys.path.insert(0, location)
    if not any(isinstance(finder, CheckoutDistributions) for finder in sys.meta_path):
        sys.meta_path.insert(0, CheckoutDistributions())
    return module_names()
