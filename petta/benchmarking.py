"""Purpose: reusable benchmark plumbing for petta and sibling packages.
Guarantees:
  - benchmark_case uses fresh untimed setup for every counter sample,
    warmup, and timed round [tested test_benchmark_case_uses_fresh_state]
  - engine regressions are decided by the minimum of three inference counts;
    wall time is recorded for advice only [tested
    test_baseline_rejects_inference_regressions_and_accepts_improvements]
  - perf instruction measurements fail loudly when perf or its event output
    fails [tested test_measure_instructions_parses_perf_csv]
Owns:
  - BenchmarkBaseline owns an update file only until its atomic replace
    completes [tested test_baseline_update_is_atomic_json]
  - measure_instructions reaps its perf process and kills its process group
    on timeout or interruption [tested
    test_perf_timeout_kills_and_reaps_process_group]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

from .atoms import Atom, Expr

_SCHEMA = 1
_COUNTER_SAMPLES = 3


def count_atoms(atom: Any) -> int:
    """Count every atom node in a term without recursing."""
    if not isinstance(atom, Atom):
        raise TypeError(f"count_atoms expects an Atom, got {type(atom).__name__}")
    count = 0
    stack = [atom]
    while stack:
        node = stack.pop()
        count += 1
        if isinstance(node, Expr):
            stack.extend(node.children)
    return count


class BenchmarkBaseline:
    """Committed counter and advisory wall baselines for benchmark_case."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        update: bool = False,
        compare_counters: bool = True,
    ):
        self.path = Path(path)
        self.update = update
        self.compare_counters = compare_counters or update
        if not self.path.is_file():
            if not update:
                raise FileNotFoundError(f"benchmark baseline does not exist: {self.path}")
            self._document: dict[str, Any] = {
                "schema": _SCHEMA,
                "counter_policy": (
                    "stats().inferences minimum of three decides; wall time advises"
                ),
                "instruction_policy": (
                    "perf instructions:u minimum of three, one percent noise allowance"
                ),
                "benchmarks": {},
            }
            return
        with self.path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if document.get("schema") != _SCHEMA:
            raise ValueError(
                f"benchmark baseline schema must be {_SCHEMA}, got {document.get('schema')!r}"
            )
        if not isinstance(document.get("benchmarks"), dict):
            raise ValueError("benchmark baseline benchmarks must be an object")
        self._document = document

    @property
    def cases(self) -> Mapping[str, Mapping[str, Any]]:
        return self._document["benchmarks"]

    def observe_counter(
        self,
        name: str,
        *,
        unit: str,
        operations: int,
        samples: Sequence[int] | None,
    ) -> int | None:
        """Record or compare one deterministic engine counter."""
        if operations <= 0:
            raise ValueError(f"benchmark operations must be positive, got {operations}")
        sample_values = None if samples is None else list(samples)
        if sample_values is not None:
            if len(sample_values) < _COUNTER_SAMPLES:
                raise ValueError(f"benchmark counter needs at least {_COUNTER_SAMPLES} samples")
            if any(
                not isinstance(value, int) or isinstance(value, bool) or value < 0
                for value in sample_values
            ):
                raise ValueError(f"invalid inference samples for {name}: {sample_values!r}")
            observed = min(sample_values)
        else:
            observed = None

        if self.update:
            previous = self._document["benchmarks"].get(name, {})
            self._document["benchmarks"][name] = {
                **previous,
                "unit": unit,
                "operations": operations,
                "inferences": observed,
            }
            return observed

        expected = self._case(name, unit=unit, operations=operations)
        baseline = expected.get("inferences")
        if observed is None:
            if baseline is not None:
                raise AssertionError(
                    f"{name} is engine-free but its baseline has inferences {baseline!r}"
                )
            return None
        if isinstance(baseline, bool) or not isinstance(baseline, int):
            raise AssertionError(f"{name} baseline has invalid inferences {baseline!r}")
        if observed > baseline:
            raise AssertionError(
                f"{name} inference regression: minimum of {sample_values!r} is "
                f"{observed}, baseline {baseline}"
            )
        return observed

    def validate_case(self, name: str, *, unit: str, operations: int) -> None:
        """Check metadata when a wall-only run deliberately skips counters."""
        if operations <= 0:
            raise ValueError(f"benchmark operations must be positive, got {operations}")
        self._case(name, unit=unit, operations=operations)

    def observe_wall(self, name: str, seconds_per_operation: float) -> None:
        """Record wall time or retain it as advisory comparison metadata."""
        if seconds_per_operation <= 0:
            raise ValueError("benchmark wall time must be positive")
        case = self._document["benchmarks"].get(name)
        if case is None:
            raise KeyError(f"benchmark {name!r} has no counter observation")
        if self.update:
            case["wall_seconds_per_operation"] = seconds_per_operation

    def observe_instructions(
        self,
        name: str,
        samples: Sequence[int],
        *,
        noise_percent: float = 1.0,
    ) -> int:
        """Record or compare perf's retired-instruction counter."""
        if (
            len(samples) < _COUNTER_SAMPLES
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
                for value in samples
            )
            or isinstance(noise_percent, bool)
            or not isinstance(noise_percent, (int, float))
            or noise_percent < 0
        ):
            raise ValueError(f"invalid instruction samples for {name}: {samples!r}")
        observed = min(samples)
        if self.update:
            case = self._document["benchmarks"].get(name)
            if case is None:
                raise KeyError(f"benchmark {name!r} has no wall/counter baseline")
            case["instructions"] = observed
            case["instruction_noise_percent"] = noise_percent
            return observed

        case = self._document["benchmarks"].get(name)
        if case is None:
            raise AssertionError(f"benchmark baseline has no case named {name!r}")
        baseline = case.get("instructions")
        allowance = case.get("instruction_noise_percent")
        if not isinstance(baseline, int) or baseline <= 0:
            raise AssertionError(f"{name} has no valid instruction baseline")
        if not isinstance(allowance, (int, float)) or allowance < 0:
            raise AssertionError(f"{name} has no valid instruction noise allowance")
        ceiling = baseline * (1.0 + allowance / 100.0)
        if observed > ceiling:
            raise AssertionError(
                f"{name} instruction regression: minimum of {list(samples)!r} is "
                f"{observed}, baseline {baseline} plus {allowance:g}% is "
                f"{ceiling:.0f}"
            )
        return observed

    def finish(self) -> None:
        """Atomically write an update; normal comparison mode writes nothing."""
        if not self.update:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self._document, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(temporary_name).replace(self.path)
            directory_descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except BaseException:
            with suppress(FileNotFoundError):
                Path(temporary_name).unlink()
            raise

    def _case(self, name: str, *, unit: str, operations: int) -> Mapping[str, Any]:
        case = self._document["benchmarks"].get(name)
        if case is None:
            raise AssertionError(
                f"benchmark baseline has no case named {name!r}; regenerate it explicitly"
            )
        if case.get("unit") != unit:
            raise AssertionError(f"{name} unit changed from {case.get('unit')!r} to {unit!r}")
        if case.get("operations") != operations:
            raise AssertionError(
                f"{name} operation count changed from {case.get('operations')!r} to {operations}"
            )
        return case


def benchmark_case(
    benchmark: Any,
    baseline: BenchmarkBaseline,
    *,
    name: str,
    unit: str,
    operations: int,
    operation: Callable[[Any], int],
    setup: Callable[[], Any],
    teardown: Callable[[Any], None],
    engine: Callable[[Any], Any] | None,
    rounds: int = 5,
    warmup_rounds: int = 2,
) -> int:
    """Measure one fixed workload through pytest-benchmark and exact counters."""

    def checked(state: Any) -> int:
        completed = operation(state)
        if completed != operations:
            raise AssertionError(f"{name} completed {completed} {unit}, expected {operations}")
        return completed

    samples: list[int] | None = None
    if engine is not None and baseline.compare_counters:
        samples = []
        for _ in range(_COUNTER_SAMPLES):
            state = setup()
            try:
                with engine(state).stats() as stats:
                    checked(state)
                samples.append(stats.inferences)
            finally:
                teardown(state)

    if baseline.compare_counters:
        inference_min = baseline.observe_counter(
            name,
            unit=unit,
            operations=operations,
            samples=samples,
        )
    else:
        baseline.validate_case(name, unit=unit, operations=operations)
        inference_min = None
    benchmark.extra_info["unit"] = unit
    benchmark.extra_info["operations_per_round"] = operations
    benchmark.extra_info["inference_samples"] = samples
    benchmark.extra_info["inference_min"] = inference_min

    def timed_setup():
        return (setup(),), {}

    result = benchmark.pedantic(
        checked,
        setup=timed_setup,
        teardown=teardown,
        rounds=rounds,
        warmup_rounds=warmup_rounds,
    )
    if benchmark.stats is not None:
        seconds_per_operation = benchmark.stats.stats.min / operations
        baseline.observe_wall(name, seconds_per_operation)
        benchmark.extra_info["wall_seconds_per_operation"] = seconds_per_operation
    return result


def measure_instructions(
    command: Sequence[str],
    *,
    rounds: int = _COUNTER_SAMPLES,
    controlled: bool = False,
    timeout: float = 60.0,
) -> tuple[int, ...]:
    """Run command under perf stat and return retired instructions per run."""
    if rounds < _COUNTER_SAMPLES:
        raise ValueError(f"instruction measurement needs at least {_COUNTER_SAMPLES} rounds")
    if not command:
        raise ValueError("instruction measurement command cannot be empty")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"instruction measurement timeout must be positive, got {timeout!r}")
    perf = shutil.which("perf")
    if perf is None:
        raise FileNotFoundError("perf is required to measure instructions:u")
    environment = os.environ | {"LC_ALL": "C"}
    samples: list[int] = []
    for _ in range(rounds):
        returncode, stdout, stderr = _run_perf(
            perf,
            command,
            environment,
            controlled=controlled,
            timeout=float(timeout),
        )
        if returncode != 0:
            detail = stderr.strip() or stdout.strip()
            raise RuntimeError(f"perf stat failed with exit {returncode}: {detail}")
        fields = [
            line.split(",", 1)[0] for line in stderr.splitlines() if ",instructions:u," in line
        ]
        if len(fields) != 1 or not fields[0].isdigit():
            raise RuntimeError(
                f"perf stat did not return one numeric instructions:u counter: {stderr.strip()}"
            )
        samples.append(int(fields[0]))
    return tuple(samples)


def _run_perf(
    executable: str,
    command: Sequence[str],
    environment: Mapping[str, str],
    *,
    controlled: bool,
    timeout: float,
) -> tuple[int, str, str]:
    """Run perf without a shell and capture both output streams."""
    with (
        tempfile.TemporaryFile() as stdout,
        tempfile.TemporaryFile() as stderr,
    ):
        child_environment = dict(environment)
        control_descriptors: tuple[int, ...] = ()
        control_arguments: list[str] = []
        if controlled:
            control_read, control_write = os.pipe()
            acknowledge_read, acknowledge_write = os.pipe()
            control_descriptors = (
                control_read,
                control_write,
                acknowledge_read,
                acknowledge_write,
            )
            for descriptor in control_descriptors:
                os.set_inheritable(descriptor, True)
            child_environment.update(
                {
                    "PETTA_PERF_CONTROL_FD": str(control_write),
                    "PETTA_PERF_ACK_FD": str(acknowledge_read),
                    "PETTA_PERF_CLOSE_FDS": f"{control_read},{acknowledge_write}",
                }
            )
            control_arguments = [
                "--delay=-1",
                f"--control=fd:{control_read},{acknowledge_write}",
            ]
        argv = [
            executable,
            "stat",
            "-x,",
            "-e",
            "instructions:u",
            *control_arguments,
            "--",
            *command,
        ]
        file_actions = [
            (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
            (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2),
        ]
        try:
            process = os.posix_spawn(
                executable,
                argv,
                child_environment,
                file_actions=file_actions,
                setpgroup=0,
            )
        finally:
            for descriptor in control_descriptors:
                os.close(descriptor)
        deadline = time.monotonic() + timeout
        try:
            while True:
                try:
                    finished, status = os.waitpid(process, os.WNOHANG)
                except InterruptedError:
                    continue
                if finished:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"perf stat exceeded its {timeout:g} second limit")
                time.sleep(min(0.01, remaining))
        except BaseException:
            with suppress(ProcessLookupError):
                os.killpg(process, signal.SIGKILL)
            with suppress(ChildProcessError):
                os.waitpid(process, 0)
            raise
        stdout.seek(0)
        stderr.seek(0)
        return (
            os.waitstatus_to_exitcode(status),
            stdout.read().decode(errors="replace"),
            stderr.read().decode(errors="replace"),
        )


__all__ = [
    "BenchmarkBaseline",
    "benchmark_case",
    "count_atoms",
    "measure_instructions",
]
