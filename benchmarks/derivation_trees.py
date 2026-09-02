"""Purpose: measure proof parsing, traversal, and first-seen projection.

The former parser performed theta(N) work with theta(D) Python frames. Its
recursive generator delegated through theta(D) frames per yielded node, making
a chain theta(N*D), or theta(N^2) when D=N. The target performs theta(N) work
with a constant Python call stack and an explicit theta(N) worst-case stack.
First-seen fact projection formerly used theta(N^2) list membership; the target
uses expected theta(N) hash membership.

Run from ``extensions/python``::

    python -m benchmarks.derivation_trees

Guarantees:
  - recursive parsing and traversal controls retain the removed depth failures
    [tested: test_recursive_derivation_controls_capture_the_depth_ceiling;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - every timed parse and traversal verifies the complete node count [tested:
    test_recursive_derivation_controls_capture_the_depth_ceiling;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - at depths 100/340/1,000/5,000 recursive parsing takes 66.530 microseconds
    then raises RecursionError, while iterative parsing takes
    109.120/357.630/1,038.250/5,329.361 microseconds; recursive traversal
    takes 28.510/269.020 microseconds then raises at 1,000, while iterative
    traversal takes 9.420/31.140/92.510/398.930 microseconds [measured: minimum
    of three process-CPU rounds; command=cd extensions/python && PYTHONPATH=.
    /home/user/Dev/.venv-pypetta/bin/python -m benchmarks.derivation_trees 100
    340 1000 5000 --facts 500 1000 2000 4000 --rounds 3;
    fixture=single-child proof chains;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - over 500/1,000/2,000/4,000 distinct facts, list membership takes
    63,532.704/245,115.897/946,034.771/3,818,650.598 microseconds while
    ordered hash membership takes 76.390/131.820/257.960/519.730 microseconds
    [measured: same command and process-CPU method; fixture=distinct root facts;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from metta import Atom, Expression, G, S
from metta.derivation import (
    Derivation,
    Fact,
    Node,
    Step,
    _node,
    _walk,
)

DEPTHS = (100, 340, 1_000, 5_000)
FACT_COUNTS = (500, 1_000, 2_000, 4_000)
ROUNDS = 3


@dataclass(frozen=True)
class DepthRow:
    """One depth and the minimum cost of each parse and traversal."""

    depth: int
    recursive_parse_us: float | None
    current_parse_us: float | None
    recursive_walk_us: float | None
    current_walk_us: float | None


@dataclass(frozen=True)
class ProjectionRow:
    """One fact count and the minimum cost of each projection."""

    count: int
    quadratic_us: float
    current_us: float


def derivation_atom(depth: int) -> Expression:
    """Build a valid derivation atom with one nested step per level."""
    if depth < 0:
        msg = f"depth must be nonnegative, got {depth}"
        raise ValueError(msg)
    call = Expression((S.call, S.recur, S.value))
    equation = Expression((S["="], S.recur, S.recur))
    node: Atom = Expression((S.fact, S["&self"], S.base))
    for _ in range(depth):
        node = Expression((S.step, call, equation, node))
    return Expression((S.derivation, Expression((S.answer, S.root, G(depth))), node))


def derivation_object(depth: int) -> Derivation:
    """Build the equivalent Python proof object without parsing."""
    node: Node = Fact("&self", S.base)
    equation = Expression((S["="], S.recur, S.recur))
    for _ in range(depth):
        node = Step(S.recur, S.value, equation, (node,))
    return Derivation(S.root, G(depth), (node,))


def recursive_from_atom(tree: Expression) -> Derivation:
    """Preserve the former recursive step conversion as the control."""
    answer = tree[1]
    return Derivation(
        answer[1],
        answer[2],
        tuple(_recursive_node(child) for child in tree.children[2:]),
    )


def _recursive_node(node: Atom) -> Node:
    if isinstance(node, Expression) and node.head == S.step:
        return _recursive_step_node(node)
    return _node(node)


def _recursive_step_node(node: Expression) -> Step:
    call = node[1]
    children = tuple(_recursive_node(child) for child in node.children[3:])
    return Step(call[1], call[2], node[2], children)


def _recursive_walk(nodes: tuple[Node, ...]) -> Iterator[Node]:
    for node in nodes:
        yield node
        if isinstance(node, Step):
            yield from _recursive_walk(node.children)


def _count_nodes(nodes: tuple[Node, ...]) -> int:
    count = 0
    stack = list(nodes)
    while stack:
        node = stack.pop()
        count += 1
        if isinstance(node, Step):
            stack.extend(node.children)
    return count


def _minimum_parse(
    parser: Callable[[Expression], Derivation],
    tree: Expression,
    expected: int,
    rounds: int,
) -> float | None:
    samples: list[float] = []
    for _ in range(rounds):
        started = time.process_time_ns()
        try:
            proof = parser(tree)
        except RecursionError:
            return None
        elapsed = time.process_time_ns() - started
        if _count_nodes(proof.children) != expected:
            msg = "a timed parser lost or duplicated proof nodes"
            raise AssertionError(msg)
        samples.append(elapsed / 1_000)
    return min(samples)


def _minimum_walk(
    walker: Callable[[tuple[Node, ...]], Iterator[Node]],
    proof: Derivation,
    expected: int,
    rounds: int,
) -> float | None:
    samples: list[float] = []
    for _ in range(rounds):
        started = time.process_time_ns()
        try:
            count = sum(1 for _ in walker(proof.children))
        except RecursionError:
            return None
        elapsed = time.process_time_ns() - started
        if count != expected:
            msg = "a timed traversal lost or duplicated proof nodes"
            raise AssertionError(msg)
        samples.append(elapsed / 1_000)
    return min(samples)


def measure_depth(depth: int, rounds: int = ROUNDS) -> DepthRow:
    """Measure parsing and traversal at one chain depth."""
    if rounds < 1:
        msg = f"rounds must be positive, got {rounds}"
        raise ValueError(msg)
    tree = derivation_atom(depth)
    proof = derivation_object(depth)
    expected = depth + 1
    return DepthRow(
        depth,
        _minimum_parse(recursive_from_atom, tree, expected, rounds),
        _minimum_parse(Derivation.from_atom, tree, expected, rounds),
        _minimum_walk(_recursive_walk, proof, expected, rounds),
        _minimum_walk(_walk, proof, expected, rounds),
    )


def _quadratic_facts(proof: Derivation) -> list[Fact]:
    seen: list[Fact] = []
    for node in _walk(proof.children):
        if isinstance(node, Fact) and node not in seen:
            seen.append(node)
    return seen


def _minimum_projection(
    project: Callable[[Derivation], list[Fact]],
    proof: Derivation,
    expected: int,
    rounds: int,
) -> float:
    samples: list[float] = []
    for _ in range(rounds):
        started = time.process_time_ns()
        facts = project(proof)
        elapsed = time.process_time_ns() - started
        if len(facts) != expected:
            msg = "a timed projection lost or duplicated facts"
            raise AssertionError(msg)
        samples.append(elapsed / 1_000)
    return min(samples)


def measure_projection(count: int, rounds: int = ROUNDS) -> ProjectionRow:
    """Measure first-seen projection over distinct root facts."""
    if count < 1 or rounds < 1:
        msg = f"count and rounds must be positive, got {count} and {rounds}"
        raise ValueError(msg)
    proof = Derivation(
        S.root,
        S.answer,
        tuple(Fact("&self", S.item(index)) for index in range(count)),
    )
    return ProjectionRow(
        count,
        _minimum_projection(_quadratic_facts, proof, count, rounds),
        _minimum_projection(lambda value: value.facts, proof, count, rounds),
    )


def _format_cost(value: float | None) -> str:
    return "RecursionError" if value is None else f"{value:10.3f} us"


def main(argv: Sequence[str] | None = None) -> int:
    """Print depth and projection measurements."""
    parser = argparse.ArgumentParser()
    parser.add_argument("depths", type=int, nargs="*", default=DEPTHS)
    parser.add_argument("--facts", type=int, nargs="+", default=FACT_COUNTS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    arguments = parser.parse_args(argv)
    for depth_row in (measure_depth(depth, arguments.rounds) for depth in arguments.depths):
        print(
            f"depth={depth_row.depth:5d} "
            f"parse-rec={_format_cost(depth_row.recursive_parse_us)} "
            f"parse-now={_format_cost(depth_row.current_parse_us)} "
            f"walk-rec={_format_cost(depth_row.recursive_walk_us)} "
            f"walk-now={_format_cost(depth_row.current_walk_us)}"
        )
    for projection_row in (
        measure_projection(count, arguments.rounds) for count in arguments.facts
    ):
        print(
            f"facts={projection_row.count:5d} "
            f"quadratic={projection_row.quadratic_us:12.3f} us "
            f"current={projection_row.current_us:10.3f} us"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
