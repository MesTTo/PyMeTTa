"""Purpose: count writes while Python definitions accumulate clauses.

Each generated clause has one main equation and one loop-helper equation.
The clauses have disjoint literal heads, so adding a clause needs to publish
only those two new atoms. Rewriting every older atom makes K definitions cost
2K squared engine calls; retaining unchanged atoms and batching each delta
makes the same workload K calls and 2K transported atoms.

Run from ``extensions/python``::

    python -m benchmarks.definition_stacking_crossings

Guarantees:
  - generated functions remain inspectable without filesystem scratch data
    [tested: test_stacked_definition_writes_scale_with_the_new_clause;
    commit=9b6695455c30809c75267c50a5137e38925af386]
  - every measured clause answers its own literal head, so a lower write count
    cannot hide a missing equation [tested:
    test_stacked_definition_writes_scale_with_the_new_clause;
    commit=9b6695455c30809c75267c50a5137e38925af386]
  - K=8/16/32 took 128/512/2,048 calls and transported the same number
    of atoms before the delta; it takes 8/16/32 calls and transports
    16/32/64 atoms after the delta [measured: exact write-call and payload
    counts at K=8/16/32; command=cd extensions/python && PYTHONPATH=.
    python -m
    benchmarks.definition_stacking_crossings 8 16 32; fixture=one main and
    one loop-helper equation per disjoint literal clause;
    commit=9b6695455c30809c75267c50a5137e38925af386]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import itertools
import linecache
import time
from collections.abc import Sequence
from dataclasses import dataclass

from metta import Grounded, Space

CLAUSES = (8, 16, 32)
_SERIALS = itertools.count()


@dataclass(frozen=True)
class Row:
    """One clause count and the writes needed to install it."""

    clauses: int
    crossings: int
    transported: int
    milliseconds: float


class _CountingSpace(Space):
    """A space that counts public write calls and their atom payloads."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.crossings = 0
        self.transported = 0

    def add(self, *atoms: object) -> None:
        if atoms:
            self.crossings += 1
            self.transported += len(atoms)
        super().add(*atoms)

    def remove(self, atom: object, *more: object) -> bool | int:
        self.crossings += 1
        self.transported += 1 + len(more)
        return super().remove(atom, *more)


def _functions(count: int) -> tuple[str, dict[str, object]]:
    """Compile inspectable functions with one helper equation apiece."""
    source = "".join(
        (
            f"def clause_{index}(value={index}):\n"
            "    total = 0\n"
            "    while total < 1:\n"
            "        total += 1\n"
            f"    return {index}\n\n"
        )
        for index in range(count)
    )
    filename = f"<definition-stacking-{next(_SERIALS)}>"
    linecache.cache[filename] = (
        len(source),
        None,
        source.splitlines(keepends=True),
        filename,
    )
    namespace: dict[str, object] = {}
    exec(compile(source, filename, "exec"), namespace)  # noqa: S102 -- local generated benchmark functions
    return filename, namespace


def measure(count: int) -> Row:
    """Install and verify ``count`` disjoint clauses under one name."""
    if count < 1:
        msg = f"count must be positive, got {count}"
        raise ValueError(msg)
    filename, namespace = _functions(count)
    function_name = f"definition-stacking-{next(_SERIALS)}"
    subject = _CountingSpace(f"&{function_name}")
    started = time.perf_counter_ns()
    try:
        for index in range(count):
            function = namespace[f"clause_{index}"]
            if not callable(function):
                msg = f"generated clause {index} is not callable"
                raise TypeError(msg)
            subject.define(function, name=function_name)
        elapsed = time.perf_counter_ns() - started
        answers = [subject.eval(f"({function_name} {index})") for index in range(count)]
        expected = [[Grounded(index)] for index in range(count)]
        if answers != expected:
            msg = f"stacked clauses answered {answers!r}, expected {expected!r}"
            raise AssertionError(msg)
        return Row(
            count,
            subject.crossings,
            subject.transported,
            elapsed / 1_000_000,
        )
    finally:
        subject.drop()
        linecache.cache.pop(filename, None)


def rows(counts: Sequence[int] = CLAUSES) -> list[Row]:
    """Measure each requested clause count in a fresh named space."""
    return [measure(count) for count in counts]


def main(argv: Sequence[str] | None = None) -> int:
    """Print crossings, transported atoms, and elapsed installation time."""
    parser = argparse.ArgumentParser()
    parser.add_argument("clauses", type=int, nargs="*", default=CLAUSES)
    arguments = parser.parse_args(argv)
    for row in rows(arguments.clauses):
        print(
            f"clauses={row.clauses:3d} crossings={row.crossings:5d} "
            f"transported={row.transported:5d} elapsed={row.milliseconds:9.3f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
