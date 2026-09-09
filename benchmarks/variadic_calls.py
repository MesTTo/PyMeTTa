"""Purpose: compare warmed variadic calls with fixed heads and equal answer bags.

Run from extensions/python with ``python -m benchmarks.variadic_calls --matrix``.
``--engine-root`` selects a provisioned control checkout. Both arms install
and warm the same pair of programs before either counter starts. The bodies
return zero; collapse consumes every answer before the next loop iteration.

Owns resources: each case releases its space; measure_instructions owns and
reaps each perf child. Missing counters and failed answer checks raise.
Guarantees: the complete matrix compares trailing and prefixed runs at
0/1/2/4/8 and two-run cut families at 2/4/8 through public Space.stats().
[tested: python -m benchmarks.variadic_calls --matrix; commit=WORKTREE]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from metta_benchmarking import measure_instructions

from benchmarks.pure import _controlled
from metta import Expression, MeTTa, S, V, arrow, equation, seg, typed

ROOT = Path(__file__).resolve().parents[3]


def call_case(family: str, arity: int, arm: str, iterations: int,
              engine_root: Path, *, controlled: bool) -> dict[str, object]:
    """Build both twins with atoms, warm both, then count one compiled loop."""
    values = list(range(arity))
    parameters = [seg(V.xs)]
    types = [S[":seg"](S.Number)]
    if family == "prefix":
        values.insert(0, 99)
        parameters.insert(0, V.first)
        types.insert(0, S.Number)
    elif family == "two":
        parameters = [seg(V.left), seg(V.right)]
    answers = arity + 1 if family == "two" else 1
    with MeTTa(metta_path=engine_root).space() as space:
        space.add(typed(S.vsum, arrow(*types, S.Number)))
        space.add(equation(Expression(S.vsum, *parameters)).to(0))
        space.add(typed(S.fsum, arrow(*([S.Number] * len(values)), S.Number)))
        fixed = [V[f"x{index}"] for index in range(len(values))]
        for _ in range(answers):
            space.add(equation(Expression(S.fsum, *fixed)).to(0))
        loops = {"variadic": S.vloop, "fixed": S.floop}
        for name, target in (("variadic", S.vsum), ("fixed", S.fsum)):
            call = Expression(target, *values)
            assert space.eval(call) == [0] * answers
            loop = loops[name]
            space.add(typed(loop, arrow(S.Number, S.Number)))
            space.add(equation(loop(V.n)).to(
                S["if"](S.eq(V.n, 0), 0,
                        S.let(V.ignored, S.collapse(call),
                              loop(S["-"](V.n, 1))))))
        for loop in loops.values():
            assert space.eval(loop(iterations)) == [0]

        def operation() -> int:
            with space.stats() as stats:
                result = space.eval(loops[arm](iterations))
            assert result == [0]
            return int(stats.inferences)

        inferences = _controlled(operation) if controlled else operation()
    return {"family": family, "arity": arity, "total_arity": len(values),
            "arm": arm, "answers_per_call": answers, "iterations": iterations,
            "inferences": inferences, "inferences_per_call": inferences / iterations}


def measure_pair(case: tuple[str, int], iterations: int,
                 engine_root: Path) -> dict[str, object]:
    """Measure each arm in fresh processes with the same setup and warmup."""
    family, arity = case
    pair: dict[str, object] = {"family": family, "arity": arity}
    for arm in ("variadic", "fixed"):
        command = [sys.executable, "-m", "benchmarks.variadic_calls",
                   "--case", family, "--arity", str(arity), "--arm", arm,
                   "--iterations", str(iterations), "--engine-root", str(engine_root)]
        # The executable and module are fixed; CLI values occupy separate argv items.
        completed = subprocess.run(command, text=True, capture_output=True, check=False)  # noqa: S603
        if completed.returncode:
            message = (f"{command!r} exited {completed.returncode}:\n"
                       f"{completed.stdout}{completed.stderr}")
            raise RuntimeError(message)
        row = json.loads(completed.stdout)
        samples = measure_instructions([*command, "--controlled"],
                                       rounds=3, controlled=True)
        row["instructions_samples"] = samples
        row["instructions_per_call"] = min(samples) / iterations
        pair[arm] = row
    return pair


def main() -> int:
    """Run one counter window or the paired matrix."""
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--matrix", action="store_true")
    action.add_argument("--case", choices=("trailing", "prefix", "two"))
    parser.add_argument("--arity", type=int, default=2)
    parser.add_argument("--arm", choices=("variadic", "fixed"), default="variadic")
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--engine-root", type=Path, default=ROOT)
    parser.add_argument("--controlled", action="store_true")
    args = parser.parse_args()
    if args.iterations <= 0 or args.arity < 0:
        parser.error("iterations must be positive and arity must be nonnegative")
    if args.controlled and args.matrix:
        parser.error("--controlled applies only to --case")
    if args.matrix:
        cases = [(family, n) for family in ("trailing", "prefix")
                 for n in (0, 1, 2, 4, 8)]
        cases += [("two", n) for n in (2, 4, 8)]
        print(json.dumps({"loadavg": os.getloadavg(),
                          "engine_root": str(args.engine_root)}), flush=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = pool.map(lambda case: measure_pair(
                case, args.iterations, args.engine_root), cases)
            for row in results:
                print(json.dumps(row), flush=True)
    else:
        print(json.dumps(call_case(args.case, args.arity, args.arm,
                                   args.iterations, args.engine_root,
                                   controlled=args.controlled)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
