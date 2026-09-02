"""Purpose: measure prefix imports made by repeated Python-name resolution.

The fixture installs one synthetic module and gives it nested attributes. A
path with P components therefore performs P candidate imports before reaching
the module on an uncached lookup. Repeating that lookup R times used to cost
theta(P*R) import attempts. The target is theta(P+R): one discovery pass and
constant import work for each successful repeat. Live attribute reads remain
linear in P because a later assignment must be visible.

Run from ``extensions/python``::

    PYTHONPATH=. python -m benchmarks.resolve_prefix_cache

Guarantees:
  - the counter wraps the exact ``importlib.import_module`` call used by the
    uncached discovery helper and verifies every returned identity [tested:
    test_repeated_resolution_reuses_the_import_plan; commit=WORKTREE]
  - at depth 4/16/64 and 1,000 repeats, uncached discovery makes
    4,000/16,000/64,000 prefix imports while the hot cache makes zero; minimum
    time across three rounds is 15.575/250.514/4293.293 against
    0.259/0.556/2.008 microseconds [measured: command=cd extensions/python &&
    PYTHONPATH=. /home/user/Dev/.venv-pypetta/bin/python -m
    benchmarks.resolve_prefix_cache 4 16 64 --repetitions 1000 --rounds 3;
    fixture=one synthetic module with live nested attributes; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
import types
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import metta_py

DEPTHS = (4, 16, 64)
REPETITIONS = 5_000
ROUNDS = 3


@dataclass(frozen=True)
class Row:
    """One path depth and both repeated-resolution strategies."""

    depth: int
    repetitions: int
    uncached_prefix_imports: int
    cached_prefix_imports: int
    uncached_microseconds: float
    cached_microseconds: float


def _trial(path: str, expected: object, repetitions: int, *, cached: bool) -> tuple[int, float]:
    """Count and time one strategy while checking every answer identity."""
    original = importlib.import_module
    prefix_imports = 0

    def counted(name: str, package: str | None = None):
        nonlocal prefix_imports
        prefix_imports += 1
        return original(name, package)

    importlib.import_module = counted
    started = time.perf_counter_ns()
    try:
        for _ in range(repetitions):
            if cached:
                result = metta_py.resolve(path)
            else:
                root, _, attrs = metta_py._find_resolve_root(path)
                result = metta_py._walk(root, attrs, path)
            if result is not expected:
                msg = f"{path!r} did not retain its final attribute identity"
                raise AssertionError(msg)
    finally:
        elapsed = time.perf_counter_ns() - started
        importlib.import_module = original
    return prefix_imports, elapsed / repetitions / 1_000


def measure(
    depth: int,
    repetitions: int = REPETITIONS,
    rounds: int = ROUNDS,
) -> Row:
    """Resolve one synthetic path repeatedly after a single warm lookup."""
    if depth < 2 or repetitions < 1 or rounds < 1:
        msg = (
            "depth must be at least 2 and repetitions and rounds positive, "
            f"got {depth}, {repetitions}, {rounds}"
        )
        raise ValueError(msg)

    root_name = "p25_resolve_benchmark_root"
    previous = sys.modules.get(root_name)
    root = types.ModuleType(root_name)
    current: Any = root
    for index in range(1, depth - 1):
        child = types.SimpleNamespace()
        setattr(current, f"part{index}", child)
        current = child
    sentinel = object()
    current.value = sentinel
    path = ".".join([root_name, *(f"part{index}" for index in range(1, depth - 1)), "value"])
    sys.modules[root_name] = root
    clear = metta_py.clear_resolve_cache
    clear()
    assert metta_py.resolve(path) is sentinel

    try:
        uncached_rows = [_trial(path, sentinel, repetitions, cached=False) for _ in range(rounds)]
        cached_rows = [_trial(path, sentinel, repetitions, cached=True) for _ in range(rounds)]
    finally:
        clear()
        if previous is None:
            sys.modules.pop(root_name, None)
        else:
            sys.modules[root_name] = previous

    uncached_imports = {imports for imports, _ in uncached_rows}
    cached_imports = {imports for imports, _ in cached_rows}
    if len(uncached_imports) != 1 or len(cached_imports) != 1:
        msg = "prefix-import counts changed between identical rounds"
        raise AssertionError(msg)
    return Row(
        depth,
        repetitions,
        uncached_imports.pop(),
        cached_imports.pop(),
        min(elapsed for _, elapsed in uncached_rows),
        min(elapsed for _, elapsed in cached_rows),
    )


def rows(
    depths: Sequence[int] = DEPTHS,
    repetitions: int = REPETITIONS,
    rounds: int = ROUNDS,
) -> list[Row]:
    """Measure each path depth with the same number of hot lookups."""
    return [measure(depth, repetitions, rounds) for depth in depths]


def main(argv: Sequence[str] | None = None) -> int:
    """Print prefix-import counts and elapsed time for each path depth."""
    parser = argparse.ArgumentParser()
    parser.add_argument("depths", type=int, nargs="*", default=DEPTHS)
    parser.add_argument("--repetitions", type=int, default=REPETITIONS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    arguments = parser.parse_args(argv)
    for row in rows(arguments.depths, arguments.repetitions, arguments.rounds):
        print(
            f"depth={row.depth:3d} repetitions={row.repetitions:6d} "
            f"imports={row.uncached_prefix_imports:8d}->{row.cached_prefix_imports:3d} "
            f"elapsed={row.uncached_microseconds:9.3f}->{row.cached_microseconds:7.3f} "
            "us/resolve"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
