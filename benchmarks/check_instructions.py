"""Purpose: compare Python and primitive-heavy engine workloads with committed
perf counters.
Guarantees:
  - each decision uses the minimum of at least three instructions:u samples
    [tested test_measure_instructions_parses_perf_csv]
  - the inventory reaches every primitive class named by the round-3 review
    [tested test_instruction_inventory_covers_primitive_heavy_engine_paths]
  - a regression in one case never hides another: every selected case is
    measured and every failure is reported before the nonzero exit. The
    stop-at-first-failure form masked four stale pins and one real overrun
    behind whichever red came first, on every tree, for days
    [tested test_check_instructions_reports_every_failing_case]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from benchmarks.pure import _CASES
from metta.testing import BenchmarkBaseline, measure_instructions


def observe_all(
    baseline: BenchmarkBaseline,
    cases: Sequence[str],
    sampler: Callable[[str], Sequence[int]],
) -> list[str]:
    """Observe every case, returning one message per failing case."""
    failures: list[str] = []
    for name in cases:
        samples = sampler(name)
        try:
            observed = baseline.observe_instructions(name, samples)
        except AssertionError as error:
            failures.append(str(error))
            print(f"{name}: samples={list(samples)} REGRESSION")
            continue
        print(f"{name}: samples={list(samples)} min={observed}")
    return failures


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

    def sampler(name: str) -> Sequence[int]:
        return measure_instructions(
            [sys.executable, "-m", "benchmarks.pure", name, "--controlled"],
            rounds=arguments.rounds,
            controlled=True,
        )

    failures = observe_all(baseline, arguments.cases, sampler)
    baseline.finish()
    if failures:
        for message in failures:
            print(message, file=sys.stderr)
        print(f"{len(failures)} case(s) regressed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
