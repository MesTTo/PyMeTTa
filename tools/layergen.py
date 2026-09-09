"""Purpose: derive the import contract and package map from BUILDS_ON.

Guarantees: both projections enumerate the declared package orders [tested:
tests/checks/check_layering_selftest.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "extensions/python"))

from metta._layers import BUILDS_ON, ORDERS, layer_groups  # noqa: E402 -- checkout declarations

BEGIN = "# begin generated package layers (extensions/python/tools/layergen.py; source=metta/_layers.py:BUILDS_ON)"
END = "# end generated package layers"
DOC_BEGIN = "<!-- begin generated package layers (extensions/python/tools/layergen.py; source=metta/_layers.py:BUILDS_ON) -->"
DOC_END = "<!-- end generated package layers -->"
CONTRACT = "package orders follow declared foundations"


def contract() -> str:
    """Render the exhaustive child layers, with equal-order siblings joined."""
    return "\n".join([
        "[[tool.importlinter.contracts]]",
        f'name = "{CONTRACT}"',
        'type = "layers"',
        'containers = ["metta"]',
        "exhaustive = true",
        "layers = [",
        *(f'    "{" | ".join(group)}",' for group in layer_groups()),
        "]",
    ])


def documentation() -> str:
    """Show each unit and its immediate foundations in computed order."""
    return "\n".join([
        "| Order | Package | Builds on |",
        "|---:|---|---|",
        *(f"| {ORDERS[name]} | `{name}` | "
          + ", ".join(f"`{base}`" for base in BUILDS_ON[name]) + " |"
          for name in sorted(BUILDS_ON, key=lambda name: (ORDERS[name], name))),
    ])


def projections(root: Path = ROOT) -> dict[Path, str]:
    """Replace the two regions owned by the package declaration."""
    from boundsgen import region  # noqa: PLC0415 -- shared strict region replacement

    manifest, guide = root / "pyproject.toml", root / "DEVELOPING.md"
    return {
        manifest: region(manifest.read_text(), BEGIN, END, contract()),
        guide: region(guide.read_text(), DOC_BEGIN, DOC_END, documentation()),
    }


def main(argv: list[str] | None = None) -> int:
    """Check the package projections or regenerate them from their declaration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for path, expected in projections().items():
        if path.read_text() != expected:
            if args.write:
                path.write_text(expected)
            else:
                stale.append(str(path.relative_to(ROOT)))
    if stale:
        print("layers-sync: stale projections: " + ", ".join(stale))
        return 1
    print(f"layers-sync: {len(BUILDS_ON)} package declarations agree with both projections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
