"""Purpose: report numeric, mixed, recursive and open Python door boundaries.

Guarantees: the report and catalog call the same source analysis; findings do
not turn this report into a gate [tested: test_door_order_report_is_not_a_gate;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

SEAT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEAT))

import doorgen  # noqa: E402 -- the checkout source precedes an installed seat

from metta.doors._order import analyse, source_text  # noqa: E402
from metta.doors._scan import core_paths  # noqa: E402


def report(root: Path = doorgen.ROOT) -> dict:
    """Return every boundary and aggregate count for the actual source tree."""
    rows = doorgen.all_rows(root)
    paths = {module: path for path, module in core_paths(root / "extensions/python/metta")}
    for row in rows:
        if row.body:
            paths.setdefault(row.body.module, doorgen.module_path(row.body.module, root))
    derived = analyse(rows, source_text(paths))
    counts = Counter("unordered" if value.number is None else str(value.number) for value in derived.values())
    return {
        "analysis": "Possible calls from a context-insensitive source graph. Open dependencies include unresolved dispatch; findings require inspection of the listed call sites.",
        "counts": dict(sorted(counts.items())),
        "first_order": sum(value.number == 1 for value in derived.values()),
        "mixed": [name for name, value in derived.items() if value.mixed],
        "open_dependencies": [name for name, value in derived.items() if value.open],
        "recursive": [name for name, value in derived.items() if value.cycles],
        "rows": {name: asdict(value) for name, value in derived.items()},
    }


def main(argv: list[str] | None = None) -> int:
    """Print the complete source-derived report without gating its findings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    result = report()
    if arguments.json:
        print(json.dumps(result, default=sorted, sort_keys=True, indent=2))
    else:
        print("door-order REPORT:", json.dumps({key: value for key, value in result.items() if key != "rows"}))
        for name, row in result["rows"].items():
            print(name, json.dumps(row, default=sorted, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
