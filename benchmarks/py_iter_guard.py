"""Purpose: price the terminal-failure guard on py-iter's per-item path.

Two costs, measured separately because they sit on opposite sides of the
crossing. The Prolog one is ``py_iter_item/2``, which every pulled item is
asked about so a raising pull can be told from an exhausted one; the Python one
is ``metta_py._guarded``, the generator that turns a raising pull into the
reserved pair. Both are paid per item on a door whose whole point is that a
million-element iterator costs no more per element than a small one.

Run from ``extensions/python``::

    PYTHONPATH=. python -m benchmarks.py_iter_guard
    PYTHONPATH=. python -m benchmarks.py_iter_guard --items 20000 --rounds 3

Inferences rather than wall clock for the Prolog half, because they are exact:
the same enumeration counts the same on a loaded box where wall clock does not
[source: DEVELOPING.md, the measurement table: "inside the engine" is
`MeTTa.stats().inferences`, min of three, and "anything: not wall clock, it
moves with scheduler load and CPU frequency"]. The Python half has no
inferences to count, so it reports nanoseconds and its own share of one pull.

Guarantees:
  - the two goals differ in exactly one conjunct, run in one process against
    one iterator source, so the difference is the guard and nothing else
  - over 20,000 items the pull costs 40,004 inferences unguarded and 60,004
    guarded, +1.00 an item and no more, while metta_py._guarded adds 5.6
    nanoseconds an item to a 9.1 nanosecond bare loop, which is 3.29 percent of
    one guarded pull's own 0.213 microseconds [measured: command=cd
    extensions/python && PYTHONPATH=. python -m benchmarks.py_iter_guard
    --items 20000 --rounds 3; fixture=one range object pulled through
    metta_py.iterate, loadavg 46.20; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import argparse
import time

import metta_py
from metta._engine import runtime

#: The two goals differ in exactly one conjunct. Both build their own source
#: through metta_py.iterate, so the Python half of the door is in both.
_PULL = (
    "metta_py_bridge, "
    "py_call(builtins:range(0, Items), Obj, [py_object(true)]), "
    "statistics(inferences, Before), "
    "forall(({body}), true), "
    "statistics(inferences, After), Spent is After - Before"
)
_PLAIN = _PULL.format(
    body="py_iter(metta_py:iterate(Obj), _R, [py_object(true), py_string_as(string)])"
)
_GUARDED = _PULL.format(
    body="py_iter(metta_py:iterate(Obj), _R, [py_object(true), py_string_as(string)]), "
    "py_iter_item(_R, _Tag)"
)


def prolog_arms(items: int, rounds: int) -> dict[str, tuple[int, float]]:
    """Inferences and seconds for `items` items, with and without the guard."""
    engine = runtime()
    goals = {
        "unguarded": _PLAIN,
        "guarded": "metta_py_bridge, py_iter_tag(_Tag), " + _GUARDED,
    }
    samples: dict[str, list[tuple[int, float]]] = {arm: [] for arm in goals}
    for _ in range(rounds):
        for arm, goal in goals.items():
            start = time.perf_counter()
            spent = engine.must(goal, Items=items)["Spent"]
            samples[arm].append((spent, time.perf_counter() - start))
    return {arm: min(values) for arm, values in samples.items()}


def python_seconds(items: int, rounds: int) -> tuple[float, float]:
    """Seconds spent draining `items` items through iterate() and through iter()."""
    wrapped = []
    bare = []
    for _ in range(rounds):
        source = range(items)
        start = time.perf_counter()
        for _value in metta_py.iterate(source):
            pass
        wrapped.append(time.perf_counter() - start)
        start = time.perf_counter()
        for _value in iter(source):
            pass
        bare.append(time.perf_counter() - start)
    return min(bare), min(wrapped)


def main() -> None:
    """Report both halves, minimum of the rounds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=20_000)
    parser.add_argument("--rounds", type=int, default=3)
    arguments = parser.parse_args()

    items = arguments.items
    arms = prolog_arms(items, arguments.rounds)
    plain, plain_seconds = arms["unguarded"]
    guarded, guarded_seconds = arms["guarded"]
    bare, wrapped = python_seconds(items, arguments.rounds)
    print(f"items                {items}")
    print(f"prolog unguarded     {plain} inferences, {plain_seconds / items * 1e6:.3f} us an item")
    print(
        f"prolog guarded       {guarded} inferences, "
        f"{guarded_seconds / items * 1e6:.3f} us an item "
        f"(+{(guarded - plain) / items:.2f} inferences an item)"
    )
    print(f"python iter()        {bare / items * 1e9:.1f} ns an item")
    print(f"python iterate()     {wrapped / items * 1e9:.1f} ns an item")
    print(
        f"python wrapper       +{(wrapped - bare) / items * 1e9:.1f} ns an item, "
        f"{(wrapped - bare) / plain_seconds * 100:.2f}% of one guarded pull"
    )


if __name__ == "__main__":
    main()
