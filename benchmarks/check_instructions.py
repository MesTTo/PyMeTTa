"""Purpose: compare Python and primitive-heavy engine workloads with committed
perf counters.
Guarantees:
  - a box that would not count is told apart from a tree that moved: this
    lane exits 0 with a named skip on a developer's box and 1 where CI=true,
    and never reports a refused measurement as a moved row
    [tested: test_a_benchmark_lane_skips_a_refusal_locally_and_refuses_it_in_ci;
    commit=11afdcdbad5bbbe37168b5d8528c23a21c42b4b6]
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
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from metta_benchmarking import BenchmarkBaseline, measure_instructions, measured_main

from benchmarks.configuration import counter_configuration
from benchmarks.pure import _CASES


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
            # Both band directions land here: a regression and an unpinned
            # improvement each fail, so the tag names the band, not one side.
            print(f"{name}: samples={list(samples)} OUTSIDE BAND")
            continue
        print(f"{name}: samples={list(samples)} min={observed}")
    return failures


def warm(case: str) -> None:
    """Boot once, unmeasured, so no sample pays for a stale engine/*.qlf.

    Both sibling harnesses have done this since they were written and this one
    did not, and the cost of the gap is measured rather than argued: with the
    .qlf set cleared, `let-heavy` reads 8,786,238,839 on its FIRST sample and
    9,111,554,612 and 9,111,517,463 on the next two, and min-of-three takes the
    first. Its committed pin is 8,786,354,108, which is that first sample, so
    the row was pinned to a boot that COMPILED the artifact set and compared
    ever after against boots that load it -- a different workload, 3.7% apart,
    with nothing in the tree deciding which one a run gets
    [source: engine/bench.py, whose header records the same hazard at
    3,129,543 inferences against 612,598; extensions/cmetta/benchmarks/bench.py,
    warm()].

    One run of the first selected case is the whole fix: the .qlf set is shared,
    so whichever case boots first warms it for every case after.
    """
    subprocess.run(  # noqa: S603  -- a fixed module of this package, named from _CASES
        [sys.executable, "-m", "benchmarks.pure", case],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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
    # Several cases boot the engine, so the C-reader mode moves their
    # instruction pins the way it moves inference pins; declare it. This
    # runner re-measures only a subset of the document, so it never
    # RESTAMPS the fingerprint the other pins were measured under.
    baseline.observe_configuration(counter_configuration(), stamp=False)

    def sampler(name: str) -> Sequence[int]:
        return measure_instructions(
            [sys.executable, "-m", "benchmarks.pure", name, "--controlled"],
            rounds=arguments.rounds,
            controlled=True,
        )

    warm(arguments.cases[0])
    failures = observe_all(baseline, arguments.cases, sampler)
    baseline.finish()
    if failures:
        for message in failures:
            print(message, file=sys.stderr)
        print(f"{len(failures)} case(s) outside the band", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(measured_main(main))
