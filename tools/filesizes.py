"""Purpose: report package source sizes and the authored share of each file.

Assumes: artifacts.ARTIFACTS declares generated output ownership.
Guarantees: generated regions are counted once, including their marker lines;
empty and singleton distributions are defined [tested:
test_file_sizes_use_declared_ownership; commit=WORKTREE].
Fails when: source is unreadable or a declared generated region is malformed.
Decides: Python, stub and Prolog source all count; 2,000 handwritten lines is
a reported review boundary, not an automatic refusal or an exception roster.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from artifacts import ARTIFACTS, ROOT, Artifact


@dataclass(frozen=True)
class FileSize:
    """Physical and generated lines of one package-relative source path."""

    path: str
    physical: int
    generated: int

    @property
    def handwritten(self) -> int:
        """Count everything not owned by an emitter."""
        return self.physical - self.generated

    @property
    def package(self) -> str:
        """Group the root and each first-level package independently."""
        parts = Path(self.path).parts
        return parts[0] if len(parts) > 1 else "."


def census(root: Path = ROOT, records: tuple[Artifact, ...] = ARTIFACTS) -> tuple[FileSize, ...]:
    """Read each source once and subtract the union of declared output lines."""
    package = root / "extensions/python/metta"
    sources = {path: path.read_text(encoding="utf-8") for path in sorted(package.rglob("*"))
               if path.is_file() and path.suffix in {".py", ".pyi", ".pl"}}
    generated: dict[Path, set[int]] = defaultdict(set)
    for artifact in records:
        for output in artifact.outputs:
            for path in output.paths(root):
                if path not in sources:
                    continue
                text = sources[path]
                start, end = output.span(text)
                if start < end:
                    first, last = text.count("\n", 0, start), text.count("\n", 0, end - 1)
                    generated[path].update(range(first, last + 1))
    return tuple(FileSize(str(path.relative_to(package)), len(text.splitlines()), len(generated[path]))
                 for path, text in sources.items())


def distribution(values: list[int]) -> dict[str, int | float | None]:
    """Use inclusive quartiles, with zero or one observation handled explicitly."""
    if not values:
        return dict.fromkeys(("min", "q1", "median", "q3", "max", "mean"))
    quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else values * 3
    return {"min": min(values), "q1": quartiles[0], "median": quartiles[1],
            "q3": quartiles[2], "max": max(values), "mean": statistics.mean(values)}


def report(files: tuple[FileSize, ...]) -> dict:
    """Derive file rows, package totals and distributions from the same census."""
    packages: dict[str, dict[str, int]] = {}
    for item in files:
        totals = packages.setdefault(item.package, {"files": 0, "physical": 0, "generated": 0, "handwritten": 0})
        totals["files"] += 1
        for key in ("physical", "generated", "handwritten"):
            totals[key] += getattr(item, key)
    rows = [asdict(item) | {"handwritten": item.handwritten} for item in files]
    return {"files": rows, "packages": packages,
            "distribution": {key: distribution([getattr(item, key) for item in files])
                             for key in ("physical", "handwritten")},
            "largest": sorted(rows, key=lambda item: (-item["physical"], item["path"]))[:10],
            "above_review_boundary": [row for row in rows if row["handwritten"] > 2000]}


def main(argv: list[str] | None = None) -> int:
    """Print a human-readable REPORT or the complete machine-readable census."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = report(census())
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print("Package source lines (.py, .pyi, .pl); generated ownership comes from artifacts.ARTIFACTS")
    print("package                    files physical generated handwritten")
    for name, totals in result["packages"].items():
        print(f"{name:26} {totals['files']:5d} {totals['physical']:8d} "
              f"{totals['generated']:9d} {totals['handwritten']:11d}")
    for kind, values in result["distribution"].items():
        print(kind + " distribution: " + ", ".join(f"{name}={value}" for name, value in values.items()))
    print("Ten largest files (physical / handwritten):")
    for item in result["largest"]:
        print(f"  {item['physical']:5d} / {item['handwritten']:5d} {item['path']}")
    print("Handwritten files above 2,000 lines (review required):")
    for item in result["above_review_boundary"]:
        print(f"  {item['handwritten']:5d} {item['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
