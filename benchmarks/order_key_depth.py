"""Purpose: measure atom ordering as expression nesting grows.

The former implementation recursively built nested tuple keys. It performed
theta(N) work, retained theta(D) Python frames, and failed at the interpreter's
recursion limit. The target keeps theta(N) work while using a constant Python
call stack, a theta(D) explicit work stack, and a theta(N) flat key.

Run from ``extensions/python``::

    python -m benchmarks.order_key_depth

Guarantees:
  - the recursive reference preserves the former expression traversal for a
    durable failure threshold and timing comparison [tested:
    test_recursive_reference_captures_the_removed_depth_failure;
    commit=WORKTREE]
  - every measured key compares with an independently produced equivalent key,
    so a reported timing cannot hide an unusable result [tested:
    test_recursive_reference_captures_the_removed_depth_failure;
    commit=WORKTREE]
  - at depths 250/500/1,000/2,000 the recursive reference takes 58.796
    microseconds then raises RecursionError, while the flat key takes
    49.834/93.220/183.898/381.238 microseconds [measured: minimum of three
    process-CPU rounds with five calls per round; command=cd extensions/python
    && PYTHONPATH=. /home/user/Dev/.venv-pypetta/bin/python -m
    benchmarks.order_key_depth 250 500 1000 2000 --repetitions 5 --rounds 3;
    fixture=unary expression chains; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from metta import Atom, Expression, G, Grounded, S, Symbol, Variable
from metta.atoms import order_key

DEPTHS = (250, 500, 1_000, 2_000)
REPETITIONS = 5
ROUNDS = 3

_ORDER_VAR, _ORDER_NUMBER, _ORDER_STRING = 0, 1, 2
_ORDER_OBJECT, _ORDER_EMPTY, _ORDER_SYMBOL, _ORDER_EXPR = 3, 4, 5, 6


@dataclass(frozen=True)
class Row:
    """One nesting depth and the minimum cost of each implementation."""

    depth: int
    recursive_microseconds: float | None
    current_microseconds: float | None
    current_items: int | None


def nested(depth: int, leaf: Atom | None = None) -> Atom:
    """Build ``depth`` unary wrappers around one leaf."""
    if depth < 0:
        msg = f"depth must be nonnegative, got {depth}"
        raise ValueError(msg)
    atom = G(0) if leaf is None else leaf
    for _ in range(depth):
        atom = Expression((S.wrap, atom))
    return atom


def _recursive_order_key(atom: Atom) -> tuple:
    """Preserve the former recursive implementation as the benchmark arm."""
    if isinstance(atom, Variable):
        return (_ORDER_VAR, atom.name)
    if isinstance(atom, Symbol):
        return (_ORDER_SYMBOL, atom.name)
    if isinstance(atom, Expression):
        if not atom.children:
            return (_ORDER_EMPTY,)
        children = tuple(_recursive_order_key(child) for child in atom.children)
        return (_ORDER_EXPR, children)
    value = atom.value if isinstance(atom, Grounded) else atom
    if isinstance(value, bool):
        return (_ORDER_SYMBOL, str(value))
    if isinstance(value, (int, float)):
        return (
            _ORDER_NUMBER,
            value,
            0 if isinstance(value, float) else 1,
        )
    if isinstance(value, str):
        return (_ORDER_STRING, value)
    return (_ORDER_OBJECT, type(value).__name__, repr(value))


def _minimum_microseconds(
    key: Callable[[Atom], tuple],
    atom: Atom,
    repetitions: int,
    rounds: int,
) -> tuple[float | None, int | None]:
    samples: list[float] = []
    width: int | None = None
    for _ in range(rounds):
        started = time.process_time_ns()
        try:
            for _ in range(repetitions):
                result = key(atom)
            elapsed = time.process_time_ns() - started
            mirror = key(atom)
            if not result <= mirror:
                msg = "equivalent ordering keys did not compare equal"
                raise AssertionError(msg)
            width = len(result)
        except RecursionError:
            return None, None
        samples.append(elapsed / repetitions / 1_000)
    return min(samples), width


def measure(
    depth: int,
    repetitions: int = REPETITIONS,
    rounds: int = ROUNDS,
) -> Row:
    """Measure the recursive reference and current implementation."""
    if repetitions < 1 or rounds < 1:
        msg = f"repetitions and rounds must be positive, got {repetitions} and {rounds}"
        raise ValueError(msg)
    atom = nested(depth)
    recursive, _ = _minimum_microseconds(
        _recursive_order_key,
        atom,
        repetitions,
        rounds,
    )
    current, width = _minimum_microseconds(
        order_key,
        atom,
        repetitions,
        rounds,
    )
    return Row(depth, recursive, current, width)


def rows(
    depths: Sequence[int] = DEPTHS,
    repetitions: int = REPETITIONS,
    rounds: int = ROUNDS,
) -> list[Row]:
    """Measure every requested nesting depth."""
    return [measure(depth, repetitions, rounds) for depth in depths]


def _format_cost(value: float | None) -> str:
    return "RecursionError" if value is None else f"{value:10.3f} us"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the recursive and current costs at each depth."""
    parser = argparse.ArgumentParser()
    parser.add_argument("depths", type=int, nargs="*", default=DEPTHS)
    parser.add_argument("--repetitions", type=int, default=REPETITIONS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    arguments = parser.parse_args(argv)
    for row in rows(arguments.depths, arguments.repetitions, arguments.rounds):
        items = "failed" if row.current_items is None else str(row.current_items)
        print(
            f"depth={row.depth:6d} recursive={_format_cost(row.recursive_microseconds)} "
            f"current={_format_cost(row.current_microseconds)} items={items}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
