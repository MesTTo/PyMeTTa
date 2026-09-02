"""Purpose: measure source-form position recovery as form count grows.

The former implementation counted newlines and searched for the last newline
from the beginning of the source for every form, taking theta(N*F) time for N
source characters and F forms. The target carries position state across
disjoint intervals, taking theta(N) time and O(1) extra space.

Run from ``extensions/python``::

    python -m benchmarks.source_form_positions

Guarantees:
  - the retained quadratic control and current implementation produce the same
    positions before their costs are reported [tested:
    test_position_tracking_scans_only_disjoint_source_intervals;
    commit=aa02d6c674b1e86eec5ddf32d111400df8f9e4b4]
  - over 1,000/2,000/4,000/8,000 forms, prefix scans take
    1,605.600/5,996.412/22,444.015/89,185.181 microseconds while carried
    positions take 412.430/913.791/1,655.250/3,437.581 microseconds
    [measured: minimum of five process-CPU rounds; command=cd
    extensions/python && PYTHONPATH=. python
    -m benchmarks.source_form_positions 1000 2000 4000 8000 --rounds 5;
    fixture=one comment and one single-line expression per form;
    commit=aa02d6c674b1e86eec5ddf32d111400df8f9e4b4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from metta import _source_forms
from metta._source_forms import SourceForm

SIZES = (500, 1_000, 2_000, 4_000)
ROUNDS = 3


@dataclass(frozen=True)
class Row:
    """One form count and the minimum process-CPU cost of each algorithm."""

    forms: int
    quadratic_us: float
    current_us: float


class _ReaderFixture:
    """Return a prepared engine-reader result without timing an engine call."""

    def __init__(self, rows: list[list[str]]) -> None:
        self.rows = rows

    def must(self, goal: str, **inputs: Any) -> dict[str, list[list[str]]]:
        if goal != "metta_py_read_forms(Source, Forms)" or "Source" not in inputs:
            msg = f"unexpected reader request: {goal}"
            raise AssertionError(msg)
        return {"Forms": self.rows}


def _fixture(count: int) -> tuple[str, list[list[str]]]:
    texts = [f"(p {index})" for index in range(count)]
    source = "".join(f"; item {index}\n{text}\n" for index, text in enumerate(texts))
    return source, [["expression", text] for text in texts]


def _quadratic_positions(source: str, rows: list[list[str]]) -> list[SourceForm]:
    """Retain the former prefix scans as the complexity control."""
    forms: list[SourceForm] = []
    cursor = 0
    for kind, text in rows:
        cursor = _source_forms._skip_between(source, cursor)
        line = 1 + source.count("\n", 0, cursor)
        column = cursor - source.rfind("\n", 0, cursor)
        forms.append(SourceForm(kind, text, line, column))
        cursor += len(text)
    return forms


def _current_positions(source: str, rows: list[list[str]]) -> list[SourceForm]:
    module: Any = _source_forms
    original = module.runtime
    module.runtime = lambda: _ReaderFixture(rows)
    try:
        return _source_forms.positioned_forms(source)
    finally:
        module.runtime = original


def _minimum(call: Callable[[], list[SourceForm]], rounds: int) -> tuple[float, list[SourceForm]]:
    samples: list[float] = []
    result: list[SourceForm] = []
    for _ in range(rounds):
        started = time.process_time_ns()
        result = call()
        samples.append((time.process_time_ns() - started) / 1_000)
    return min(samples), result


def measure(count: int, rounds: int = ROUNDS) -> Row:
    """Measure both algorithms after requiring byte-for-byte equal rows."""
    if count < 1 or rounds < 1:
        msg = f"count and rounds must be positive, got {count} and {rounds}"
        raise ValueError(msg)
    source, rows = _fixture(count)
    quadratic_us, expected = _minimum(
        lambda: _quadratic_positions(source, rows), rounds
    )
    current_us, actual = _minimum(lambda: _current_positions(source, rows), rounds)
    if actual != expected:
        msg = "position algorithms produced different source rows"
        raise AssertionError(msg)
    return Row(count, quadratic_us, current_us)


def main(argv: list[str] | None = None) -> int:
    """Print a scaling ladder for the quadratic control and current code."""
    parser = argparse.ArgumentParser()
    parser.add_argument("sizes", nargs="*", type=int, default=list(SIZES))
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    args = parser.parse_args(argv)
    print("forms quadratic_us current_us")
    for count in args.sizes:
        row = measure(count, args.rounds)
        print(f"{row.forms:5d} {row.quadratic_us:12.3f} {row.current_us:10.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
