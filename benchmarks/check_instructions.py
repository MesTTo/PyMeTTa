"""Purpose: compare Python and primitive-heavy engine workloads with committed
perf counters.
Guarantees:
  - each decision uses the minimum of at least three instructions:u samples
    [tested test_measure_instructions_parses_perf_csv]
  - the inventory reaches every primitive class named by the round-3 review
    [tested test_instruction_inventory_covers_primitive_heavy_engine_paths]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from benchmarks.pure import _CASES
from metta.testing import BenchmarkBaseline, measure_instructions


def main(argv: Sequence[str] | None = None) -> int:
    """Measure selected cases and update or compare their counters."""
    parser = argparse.ArgumentParser()
    names = tuple(sorted(_CASES))
    parser.add_argument("cases", nargs="*", choices=names, default=names)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--update", action="store_true")
    arguments = parser.parse_args(argv)

    directory = Path(__file__).resolve().parent
    baseline = BenchmarkBaseline(directory / "baseline.json", update=arguments.update)
    for name in arguments.cases:
        samples = measure_instructions(
            [sys.executable, "-m", "benchmarks.pure", name, "--controlled"],
            rounds=arguments.rounds,
            controlled=True,
        )
        observed = baseline.observe_instructions(name, samples)
        print(f"{name}: samples={list(samples)} min={observed}")
    baseline.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
