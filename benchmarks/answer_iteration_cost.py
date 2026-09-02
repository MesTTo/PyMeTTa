"""Purpose: measure caller-position bookkeeping on repeated Answers iteration.

The generated drivers put the same ``for value in answers`` operation after
increasing amounts of bytecode. CPython maps a frame's instruction offset to
its source column by walking ``code.co_positions()`` up to that offset, so the
old per-iteration lookup grew with both the number of iterations and the
amount of preceding bytecode. The target is one linear derivation per call
site followed by constant-time lookups.

Run from ``extensions/python``::

    python -m benchmarks.answer_iteration_cost

Guarantees:
  - every row repeats one already-warmed one-answer view, so construction,
    source parsing, and the first position-table build stay outside timing
    [tested: test_answer_iteration_benchmark_reuses_one_warmed_view;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
  - padding changes the call-site instruction offset without changing the
    measured iteration count or answer [tested:
    test_answer_iteration_benchmark_reuses_one_warmed_view;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
  - at 0, 1,000, and 4,000 skipped operations, the old linear lookup took
    15.70, 358.81, and 1,356.07 microseconds per iteration; the weak call-site
    cache took 3.39, 3.27, and 3.33 microseconds [measured: 2,000
    warmed one-answer iterations, minimum of 3 rounds; command=cd
    extensions/python && PYTHONPATH=. /home/user/Dev/.venv-pypetta/bin/python
    -m benchmarks.answer_iteration_cost --calls 2000 --rounds 3;
    fixture=CPython 3.14, paddings 0/1000/4000;
    commit=0ffac1f272c65d1c3742a2bfb824538e426c264a]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from dataclasses import dataclass
from types import FunctionType

from metta.results import Answers

CALLS = 2_000
PADDINGS = (0, 1_000, 4_000)
ROUNDS = 3


@dataclass(frozen=True)
class Row:
    """One generated call site's bytecode size and steady-state cost."""

    padding: int
    positions: int
    nanoseconds: float


def driver(padding: int) -> tuple[FunctionType, int]:
    """Build a driver whose Answers loop follows ``padding`` skipped ops."""
    if padding < 0:
        msg = f"padding must be non-negative, got {padding}"
        raise ValueError(msg)
    source = [
        "def drive(view, calls):",
        "    total = 0",
        "    if calls < 0:",
        "        pass",
    ]
    # The branch jumps over this bytecode for every accepted call count. It
    # moves the iteration instruction without adding padding work to timing.
    source.extend("        total += 0" for _ in range(padding))
    source.extend(
        (
            "    for _ in range(calls):",
            "        for value in view:",
            "            total += value",
            "    return total",
        )
    )
    namespace: dict[str, object] = {}
    code = compile("\n".join(source), __file__, "exec")
    exec(code, namespace)  # noqa: S102 -- generated local benchmark driver
    drive = namespace["drive"]
    if not isinstance(drive, FunctionType):
        msg = "the generated answer-iteration driver is not a function"
        raise TypeError(msg)
    return drive, len(tuple(drive.__code__.co_positions()))


def rows(
    calls: int = CALLS,
    paddings: Sequence[int] = PADDINGS,
    rounds: int = ROUNDS,
) -> list[Row]:
    """Measure each warmed call site with the same answer and operation count."""
    if calls < 1 or rounds < 1:
        msg = f"calls and rounds must be positive, got {calls} and {rounds}"
        raise ValueError(msg)
    measured = []
    for padding in paddings:
        drive, positions = driver(padding)
        answers = Answers([1], space="&answer-iteration-cost")
        assert drive(answers, 1) == 1
        samples = []
        for _ in range(rounds):
            started = time.perf_counter_ns()
            completed = drive(answers, calls)
            samples.append(time.perf_counter_ns() - started)
            if completed != calls:
                msg = f"the driver completed {completed} of {calls} answer reads"
                raise AssertionError(msg)
        measured.append(Row(padding, positions, min(samples) / calls))
    return measured


def main(argv: Sequence[str] | None = None) -> int:
    """Print the minimum steady-state nanoseconds per Answers iteration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=CALLS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    arguments = parser.parse_args(argv)
    for row in rows(calls=arguments.calls, rounds=arguments.rounds):
        print(
            f"padding={row.padding:4d} positions={row.positions:5d} "
            f"iteration={row.nanoseconds:10.1f} ns"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
