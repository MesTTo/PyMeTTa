"""Purpose: compare engine-free workloads with committed perf counters.
Guarantees:
  - each decision uses the minimum of at least three instructions:u samples
    [tested test_measure_instructions_parses_perf_csv]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from petta.testing import BenchmarkBaseline, measure_instructions

_CASES = ("term-operators", "wire-codec")


def main(argv: Sequence[str] | None = None) -> int:
    """Measure selected cases and update or compare their counters."""
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", choices=_CASES, default=_CASES)
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
