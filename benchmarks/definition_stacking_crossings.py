"""Purpose: count writes while Python definitions accumulate clauses.

Each generated clause has one main equation and one loop-helper equation.
The clauses have disjoint literal heads, so adding a clause needs to publish
only those two new atoms. Rewriting every older atom makes K definitions cost
2K squared engine calls; retaining unchanged atoms and batching each delta
makes the same workload K calls and 2K transported atoms.

A define publishes every engine write it makes in one crossing,
`metta._declare.definitions._publish` (metta_py_publish_definition/2), so a
crossing here is one publication that wrote into the subject space and the
atoms transported are what those publications added to or removed from it;
the reflection rows a publication writes into &metta are not the space's.

Run from ``extensions/python``::

    python -m benchmarks.definition_stacking_crossings

Guarantees:
  - generated functions remain inspectable without filesystem scratch data
    [tested 2026-09-30T13:57:54+10:00: test_stacked_definition_writes_scale_with_the_new_clause]
  - every measured clause answers its own literal head, so a lower write count
    cannot hide a missing equation [tested 2026-09-30T13:57:54+10:00:
    test_stacked_definition_writes_scale_with_the_new_clause]
  - a publication that writes nothing into the subject space is not counted,
    so a define that stopped writing through `_publish` reads 0 crossings
    and fails the test rather than passing on a blind counter
    [tested 2026-09-30T13:57:54+10:00: test_stacked_definition_writes_scale_with_the_new_clause]
  - K=8/16/32 took 128/512/2,048 calls and transported the same number
    of atoms before the delta (9b6695455c30809c75267c50a5137e38925af386);
    K defines take K publications transporting 2K atoms, the new clause's
    two equations each [measured 2026-09-30T13:58:08+10:00: exact publication
    and payload counts at K=8/16/32; command=cd extensions/python &&
    PYTHONPATH=. python -c "from benchmarks.definition_stacking_crossings
    import rows; print(rows((8, 16, 32)))"; fixture=one main and one
    loop-helper equation per disjoint literal clause]
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
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import metta._declare.definitions as _definitions
from benchmarks import decide_width
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


@dataclass
class _Publications:
    """The define publications that wrote into one space, and their atoms."""

    space: str
    crossings: int = 0
    transported: int = 0


@contextmanager
def _counted(space: str) -> Iterator[_Publications]:
    """Count every define publication writing into ``space`` while the block runs.

    `_publish` is looked up in its module at each call, so the wrapper sees
    every define; it is put back however the block ends.
    """
    counts = _Publications(space)
    publish = _definitions._publish

    def counted(target: Any, writes: list[list[Any]], watches: list[list[Any]]) -> BaseException | None:
        # A write is [add|remove, SpaceName, Wires] (_binding/store.pl).
        into = sum(len(wires) for _edge, written, wires in writes if written == space)
        if into:
            counts.crossings += 1
            counts.transported += into
        return publish(target, writes, watches)

    _definitions._publish = counted
    try:
        yield counts
    finally:
        _definitions._publish = publish


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
    subject = Space(f"&{function_name}")
    started = time.perf_counter_ns()
    try:
        with _counted(subject.name) as counts:
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
            counts.crossings,
            counts.transported,
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
    decide_width("measures")
    for row in rows(arguments.clauses):
        print(
            f"clauses={row.clauses:3d} crossings={row.crossings:5d} "
            f"transported={row.transported:5d} elapsed={row.milliseconds:9.3f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
