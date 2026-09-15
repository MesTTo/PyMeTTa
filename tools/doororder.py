"""Purpose: gate defects while reporting every unordered Python door boundary.

Guarantees: the report and catalog call the same source analysis. Mixed,
recursive and undeclared open boundaries fail. Supplied parameter contracts
and their dependent doors stay unordered and remain visible
[tested: test_door_order_gate_refuses_each_boundary_defect,
test_declared_supplied_callable_is_unordered_by_contract,
test_composition_of_contract_open_door_is_unordered_by_dependency; commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from graphlib import TopologicalSorter
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
    permitted = {name for name, value in derived.items() if value.number is not None}
    candidates = {name: value.blocked_by for name, value in derived.items()
                  if value.number is None and not (value.mixed or value.cycles or value.defect_open)}
    for name in TopologicalSorter(candidates).static_order():
        if name in candidates and candidates[name] <= permitted:
            permitted.add(name)
    return {
        "analysis": "Possible calls from a context-insensitive source graph. Declared caller-implemented contracts stay open; mixed crossings, recursion and other unresolved dispatch fail the gate. Every open call retains its owning source site.",
        "counts": dict(sorted(counts.items())),
        "first_order": sum(value.number == 1 for value in derived.values()),
        "mixed": [name for name, value in derived.items() if value.mixed],
        "open_dependencies": [name for name, value in derived.items() if value.open],
        "defect_open_dependencies": [name for name, value in derived.items() if value.defect_open],
        "unordered_by_contract": [name for name, value in derived.items()
                                  if name in permitted and value.number is None and value.contracts],
        "unordered_by_dependency": [name for name, value in derived.items()
                                    if name in permitted and value.number is None and not value.contracts],
        "recursive": [name for name, value in derived.items() if value.cycles],
        "rows": {name: {**asdict(value),
                        "contracts": [asdict(call) for call in sorted(value.contracts,
                                      key=lambda call: (call.site, call.parameter, call.annotation))]}
                 for name, value in derived.items()},
    }


def main(argv: list[str] | None = None) -> int:
    """Print every source-derived boundary and fail on unresolved findings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    result = report()
    if arguments.json:
        print(json.dumps(result, default=sorted, sort_keys=True, indent=2))
    else:
        print("door-order GATE:", json.dumps({key: value for key, value in result.items() if key != "rows"}))
        for name, row in result["rows"].items():
            print(name, json.dumps(row, default=sorted, sort_keys=True))
    return int(any(result[key] for key in ("mixed", "defect_open_dependencies", "recursive")))


if __name__ == "__main__":
    raise SystemExit(main())
