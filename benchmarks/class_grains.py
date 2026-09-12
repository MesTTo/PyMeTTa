"""Purpose: measure declaration, construction, field access and grain storage.
Assumes:
  - native engine artifacts are built and memory_scale's Linux/SWI counters are
    available [source: extensions/python/benchmarks/memory_scale.py:_measure;
    commit=WORKTREE]
Guarantees:
  - each grain/population sample has a fresh process; creation retains every
    native receiver, while reads and writes use the last receiver in that
    population [tested: python -m benchmarks.class_grains --sizes 1 100 1000;
    commit=WORKTREE]
Owns resources:
  - the MeTTa context retires the class and all prototype spaces; the parent
    waits for each sample process to finish before starting the next.
Decides:
  - native module bytes include class and private-space storage/execution;
    Python bytes report retained crossing objects separately. Neither metric
    claims complete process memory [source:
    extensions/python/benchmarks/memory_scale.py:_space_module_snapshot;
    commit=WORKTREE]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from benchmarks.memory_scale import _measure, _space_module_snapshot, _sum_live_module_bytes
from metta import Expression, MeTTa, S, Space
from metta._declare.classes import declaration


@dataclass(frozen=True, slots=True)
class CostValue:
    x: int
    y: int
    z: int


@dataclass(slots=True)
class CostEntity:
    x: int
    y: int
    z: int


@dataclass
class CostPrototype(Space):
    x: int
    y: int
    z: int


CLASSES = {"value": CostValue, "entity": CostEntity, "prototype": CostPrototype}


def _call(space: Space, source: str) -> Any:
    answers = space.run(source)
    if len(answers) != 1 or len(answers[0]) != 1:
        raise AssertionError(f"{source} must answer once: {answers}")
    answer = answers[0][0]
    if isinstance(answer, Expression) and answer.head == S.Error:
        raise AssertionError(f"{source} answered {answer}")
    return answer


def _access(space: Space, source: str, expected: Any) -> dict[str, Any]:
    samples = []
    for _ in range(5):
        with space.stats() as stats:
            answer = _call(space, source)
        if answer != expected:
            raise AssertionError(f"{source} answered {answer}, expected {expected}")
        samples.append(stats.inferences)
    return {"min": min(samples), "max": max(samples), "samples": samples}


def sample(grain: str, size: int) -> dict[str, Any]:
    with MeTTa() as context:
        root, cls = context.self, CLASSES[grain]
        with root.stats() as declared:
            root.define(cls)
        plan = declaration(cls)
        declaration_bytes = _space_module_snapshot(plan.space)
        create = f"!(make-{plan.name} 1 2 3)"
        warm = _call(root, create)
        _call(root, f"!({plan.name}-x {warm})")
        if grain != "value":
            _call(root, f"!({plan.name}-x! {warm} 1)")
            _call(root, f"!(retire-{plan.name} {warm})")

        receivers = []

        def construct() -> int:
            receivers.extend(_call(root, create) for _ in range(size))
            return len(receivers)

        def retained(_count: int) -> dict[str, int]:
            private = ([Space(receiver.args[0], _runtime=root._rt) for receiver in receivers]
                       if grain == "prototype" else [])
            return {"private_module_bytes": _sum_live_module_bytes(private),
                    "private_spaces": len(private), "receivers": len(receivers)}

        creation = _measure(plan.space, construct, extras=retained)
        creation["native_module_bytes"] = (creation["storage_module_bytes"]
                                            + creation["execution_module_bytes"]
                                            + creation["private_module_bytes"])
        receiver = receivers[-1]
        read = _access(root, f"!({plan.name}-x {receiver})", 1)
        write_source = f"!(make-{plan.name} 4 2 3)" if grain == "value" else f"!({plan.name}-x! {receiver} 4)"
        expected = S[plan.name](4, 2, 3) if grain == "value" else True
        write = _access(root, write_source, expected)
        return {"grain": grain, "size": size,
                "declaration_inferences": declared.inferences,
                "declaration_modules": declaration_bytes,
                "creation": creation, "read_inferences": read,
                "write_inferences": write}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", nargs="+", type=int, default=[1, 100, 1000])
    parser.add_argument("--sample", choices=CLASSES)
    args = parser.parse_args()
    if any(size < 1 for size in args.sizes):
        parser.error("population sizes must be positive")
    if args.sample:
        if len(args.sizes) != 1:
            parser.error("a sample requires exactly one population size")
        print(json.dumps(sample(args.sample, args.sizes[0]), sort_keys=True))
        return
    for grain in CLASSES:
        for size in args.sizes:
            completed = subprocess.run(
                [sys.executable, "-m", "benchmarks.class_grains", "--sample", grain,
                 "--sizes", str(size)], check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
