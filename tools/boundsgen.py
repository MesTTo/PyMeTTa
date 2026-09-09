"""Purpose: derive configure parameters and setting documentation from descriptors.

Guarantees: every effective Setting appears in the exact configure signature
and its documented policy [tested:
test_setting_declaration_reaches_every_projection; commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "extensions/python"))

from metta._catalog.bounds import Config, settings  # noqa: E402  -- the tool runs from its checkout

BEGIN = "    # begin generated configure (tools/boundsgen.py; source=Setting declarations)"
END = "    # end generated configure"
DOC_BEGIN = "<!-- begin generated settings (extensions/python/tools/boundsgen.py; source=_catalog/bounds.py:Setting) -->"
DOC_END = "<!-- end generated settings -->"


def configure_source(owner: type = Config) -> str:
    """Emit real parameters so Python, help and type checkers read one shape."""
    names = settings(owner)
    lines = ["    def configure(", "        self,"]
    if names:
        lines.append("        *,")
    lines.extend(f"        {name}: int | _Unset = _UNSET," for name in names)
    lines.extend([
        "    ) -> None:",
        '        """Validate every supplied setting and replace its local or catalog value.',
        "",
        "        Live values use one engine transaction. An enclosing transaction",
        "        owns its commit; private configurations only change their own bag.",
        '        """',
        "        self._configure({",
        *(f'            "{name}": {name},' for name in names),
        "        })",
    ])
    return "\n".join(lines)


def documentation(owner: type = Config) -> str:
    """Render names, defaults and policy from the effective descriptors."""
    lines = [
        "| Setting | Default | Environment | Lifetime | Purpose |",
        "|---|---:|---|---|---|",
    ]
    for name, field in settings(owner).items():
        help_text = (field.__doc__ or "").replace("|", "&#124;").replace("\n", " ")
        lines.append(
            f"| `{name}` | {field.default} | {field.environment or ''} | "
            f"{'startup' if field.startup else 'catalog row'} | {help_text} |"
        )
    return "\n".join(lines)


def region(source: str, begin: str, end: str, value: str) -> str:
    """Replace one named generated region, refusing ambiguous ownership."""
    if source.count(begin) != 1 or source.count(end) != 1:
        msg = f"expected exactly one generated region: {begin}"
        raise ValueError(msg)
    head, remaining = source.split(begin)
    _, tail = remaining.split(end)
    return head + begin + "\n" + value + "\n" + end + tail


def projections(root: Path = ROOT) -> dict[Path, str]:
    """Read declarations once and derive each file's owned region."""
    bounds = root / "extensions/python/metta/_catalog/bounds.py"
    guide = root / "DEVELOPING.md"
    return {
        bounds: region(bounds.read_text(), BEGIN, END, configure_source()),
        guide: region(guide.read_text(), DOC_BEGIN, DOC_END, documentation()),
    }


def main(argv: list[str] | None = None) -> int:
    """Check every projection or write the forms declared by the descriptors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for path, wanted in projections().items():
        if path.read_text() != wanted:
            if args.write:
                path.write_text(wanted)
            else:
                stale.append(str(path.relative_to(ROOT)))
    if stale:
        print("bounds-sync: stale projections: " + ", ".join(stale))
        return 1
    print(f"bounds-sync: {len(settings(Config))} setting declarations agree with both projections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
