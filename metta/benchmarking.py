"""Purpose: reusable benchmark plumbing for metta and sibling packages.
Guarantees:
  - benchmark_case uses fresh untimed setup for every counter sample,
    warmup, and timed round [tested test_benchmark_case_uses_fresh_state]
  - engine movement is decided by the minimum of three inference counts
    against a TWO-SIDED band: a drop beyond the allowance fails as a stale
    pin, because a stale-high pin masks regressions up to its own margin;
    wall time is recorded for advice only [tested
    test_baseline_rejects_inference_movement_beyond_the_allowance]
  - counter slopes compare the inference growth between two fixed workload
    sizes, with fresh state at each point and the same two-sided band
    [tested test_benchmark_counter_slope_uses_fresh_state_and_gates_growth]
  - instruction pins band on both sides of the noise allowance [tested
    test_baseline_bands_instructions_on_both_sides]
  - counter comparisons declare their measurement configuration and refuse a
    missing or differing stamp, because artifact presence alone has moved a
    pin 12x with zero code change [tested
    test_baseline_stamps_and_verifies_counter_configuration,
    test_baseline_without_configuration_stamp_refuses_counter_comparison]
  - perf instruction measurements fail loudly when perf or its event output
    fails [tested test_measure_instructions_parses_perf_csv]
Owns:
  - BenchmarkBaseline owns an update file only until its atomic replace
    completes [tested test_baseline_update_is_atomic_json]; update mode may
    prune a case nothing measures [tested
    test_baseline_remove_case_is_update_only], and a subset updater
    verifies the configuration stamp without rewriting it [tested
    test_a_subset_updater_verifies_without_restamping]
  - measure_instructions reaps its perf process and kills its process group
    on timeout or interruption [tested
    test_perf_timeout_kills_and_reaps_process_group]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

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

from .atoms import Atom, Expression

_SCHEMA = 1
_COUNTER_SAMPLES = 3
# A regression must clear a small absolute allowance. The join benchmarks
# reproduce a +2 shift that three measurements prove is not work: the changed
# predicates are never called, the delta does not scale with the workload,
# and an unrelated edit cancels it. Real regressions scale with operations,
# so at these workload sizes a handful of inferences is four orders of
# magnitude below anything worth catching, while a real per-operation shift
# still lands far above the allowance.
_COUNTER_TOLERANCE = 4


def count_atoms(atom: Any) -> int:
    """Count every atom node in a term without recursing."""
    if not isinstance(atom, Atom):
        msg = f"count_atoms expects an Atom, got {type(atom).__name__}"
        raise TypeError(msg)
    count = 0
    stack = [atom]
    while stack:
        node = stack.pop()
        count += 1
        if isinstance(node, Expression):
            stack.extend(node.children)
    return count


def _counter_observation(
    name: str,
    samples: Sequence[int] | None,
) -> tuple[list[int] | None, int | None]:
    sample_values = None if samples is None else list(samples)
    if sample_values is None:
        return None, None
    if len(sample_values) < _COUNTER_SAMPLES:
        msg = f"benchmark counter needs at least {_COUNTER_SAMPLES} samples"
        raise ValueError(msg)
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in sample_values
    ):
        msg = f"invalid inference samples for {name}: {sample_values!r}"
        raise ValueError(msg)
    return sample_values, min(sample_values)


def _compare_counter(
    name: str,
    expected: Mapping[str, Any],
    sample_values: list[int] | None,
    observed: int | None,
) -> int | None:
    baseline = expected.get("inferences")
    if observed is None:
        if baseline is not None:
            msg = f"{name} is engine-free but its baseline has inferences {baseline!r}"
            raise AssertionError(
                msg
            )
        return None
    if isinstance(baseline, bool) or not isinstance(baseline, int):
        msg = f"{name} baseline has invalid inferences {baseline!r}"
        raise AssertionError(msg)  # noqa: TRY004  -- the harness is checking its own invariant, so AssertionError is the intended contract
    if observed > baseline + _COUNTER_TOLERANCE:
        msg = (
            f"{name} inference regression: minimum of {sample_values!r} is "
            f"{observed}, baseline {baseline} plus the {_COUNTER_TOLERANCE} "
            f"inference allowance"
        )
        raise AssertionError(
            msg
        )
    #The band is two-sided because a stale-high pin masks real regressions
    #up to its own margin: file-load sat at 8704891 while the tree measured
    #722264, so anything under 12x slower would still have read green. A
    #drop beyond the allowance therefore fails until the pin is re-measured
    #and its mechanism recorded beside it.
    if observed < baseline - _COUNTER_TOLERANCE:
        msg = (
            f"{name} inference improvement left unpinned: minimum of "
            f"{sample_values!r} is {observed}, baseline {baseline} minus the "
            f"{_COUNTER_TOLERANCE} inference allowance; re-pin with "
            f"--update-baseline and record the mechanism beside the pin"
        )
        raise AssertionError(
            msg
        )
    return observed


def _counter_samples(
    operation: Callable[[Any], int],
    *,
    operations: int,
    setup: Callable[[], Any],
    teardown: Callable[[Any], None],
    engine: Callable[[Any], Any],
) -> list[int]:
    samples = []
    for _ in range(_COUNTER_SAMPLES):
        state = setup()
        try:
            with engine(state).stats() as stats:
                completed = operation(state)
            if completed != operations:
                msg = f"counter sample completed {completed} operations, expected {operations}"
                raise AssertionError(
                    msg
                )
            samples.append(stats.inferences)
        finally:
            teardown(state)
    return samples


def _required_counter_observation(name: str, samples: Sequence[int]) -> tuple[list[int], int]:
    values, observed = _counter_observation(name, samples)
    if values is None or observed is None:
        msg = f"{name} lost its required inference samples"
        raise RuntimeError(msg)
    return values, observed


def _counter_slope_observation(
    name: str,
    small_operations: int,
    large_operations: int,
    small_samples: Sequence[int],
    large_samples: Sequence[int],
) -> tuple[list[int], list[int], int]:
    if small_operations <= 0 or large_operations <= small_operations:
        msg = "counter slope needs positive operation counts in increasing order"
        raise ValueError(msg)
    small_values, small = _required_counter_observation(f"{name} small", small_samples)
    large_values, large = _required_counter_observation(f"{name} large", large_samples)
    observed = large - small
    if observed < 0:
        msg = f"{name} inference count fell from {small} to {large} as the workload grew"
        raise ValueError(
            msg
        )
    return small_values, large_values, observed


def _counter_slope_case(
    document: Mapping[str, Any], name: str, unit: str
) -> dict[str, Any]:
    case = document["benchmarks"].get(name)
    if case is None:
        msg = f"benchmark {name!r} has no counter observation"
        raise KeyError(msg)
    if case.get("unit") != unit:
        msg = f"{name} unit changed from {case.get('unit')!r} to {unit!r}"
        raise AssertionError(msg)
    return case


def _compare_counter_slope(
    name: str,
    expected: Any,
    *,
    small_operations: int,
    large_operations: int,
    small_values: list[int],
    large_values: list[int],
    observed: int,
) -> int:
    if not isinstance(expected, dict):
        msg = f"{name} has no valid inference slope baseline"
        raise AssertionError(msg)  # noqa: TRY004  -- the harness is checking its own invariant, so AssertionError is the intended contract
    if expected.get("small_operations") != small_operations:
        msg = (
            f"{name} slope small operation count changed from "
            f"{expected.get('small_operations')!r} to {small_operations}"
        )
        raise AssertionError(
            msg
        )
    if expected.get("large_operations") != large_operations:
        msg = (
            f"{name} slope large operation count changed from "
            f"{expected.get('large_operations')!r} to {large_operations}"
        )
        raise AssertionError(
            msg
        )
    baseline = expected.get("delta_inferences")
    if isinstance(baseline, bool) or not isinstance(baseline, int) or baseline < 0:
        msg = f"{name} has an invalid inference slope baseline"
        raise AssertionError(msg)
    if observed > baseline + _COUNTER_TOLERANCE:
        msg = (
            f"{name} inference slope regression: {large_values!r} minus "
            f"{small_values!r} has minimum growth {observed}, baseline {baseline} "
            f"plus the {_COUNTER_TOLERANCE} inference allowance"
        )
        raise AssertionError(
            msg
        )
    if observed < baseline - _COUNTER_TOLERANCE:
        msg = (
            f"{name} inference slope improvement left unpinned: {large_values!r} "
            f"minus {small_values!r} has minimum growth {observed}, baseline "
            f"{baseline} minus the {_COUNTER_TOLERANCE} inference allowance; "
            f"re-pin with --update-baseline and record the mechanism beside the pin"
        )
        raise AssertionError(
            msg
        )
    return observed


def _instruction_observation(
    name: str,
    samples: Sequence[int],
    noise_percent: float,
) -> int:
    invalid_samples = len(samples) < _COUNTER_SAMPLES or any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in samples
    )
    invalid_noise = (
        isinstance(noise_percent, bool)
        or not isinstance(noise_percent, (int, float))
        or noise_percent < 0
    )
    if invalid_samples or invalid_noise:
        msg = f"invalid instruction samples for {name}: {samples!r}"
        raise ValueError(msg)
    return min(samples)


def _compare_instructions(
    name: str,
    case: Mapping[str, Any],
    samples: Sequence[int],
    observed: int,
) -> int:
    baseline = case.get("instructions")
    allowance = case.get("instruction_noise_percent")
    if not isinstance(baseline, int) or baseline <= 0:
        msg = f"{name} has no valid instruction baseline"
        raise AssertionError(msg)
    if not isinstance(allowance, (int, float)) or allowance < 0:
        msg = f"{name} has no valid instruction noise allowance"
        raise AssertionError(msg)
    ceiling = baseline * (1.0 + allowance / 100.0)
    if observed > ceiling:
        msg = (
            f"{name} instruction regression: minimum of {list(samples)!r} is "
            f"{observed}, baseline {baseline} plus {allowance:g}% is "
            f"{ceiling:.0f}"
        )
        raise AssertionError(
            msg
        )
    floor = baseline * (1.0 - allowance / 100.0)
    if observed < floor:
        msg = (
            f"{name} instruction improvement left unpinned: minimum of "
            f"{list(samples)!r} is {observed}, baseline {baseline} minus "
            f"{allowance:g}% is {floor:.0f}; re-pin with --update and record "
            f"the mechanism beside the pin"
        )
        raise AssertionError(
            msg
        )
    return observed


class BenchmarkBaseline:
    """Committed counter and advisory wall baselines for benchmark_case."""

    def __init__(  # noqa: D107  -- the enclosing class documents construction and the object invariants
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
                msg = f"benchmark baseline does not exist: {self.path}"
                raise FileNotFoundError(msg)
            self._document: dict[str, Any] = {
                "schema": _SCHEMA,
                "counter_policy": (
                    "stats().inferences minimum of three and fixed two-point growth "
                    "slopes decide; wall time advises"
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
            msg = f"benchmark baseline schema must be {_SCHEMA}, got {document.get('schema')!r}"
            raise ValueError(
                msg
            )
        if not isinstance(document.get("benchmarks"), dict):
            msg = "benchmark baseline benchmarks must be an object"
            raise ValueError(msg)  # noqa: TRY004  -- the harness is checking its own invariant, so AssertionError is the intended contract
        self._document = document

    @property
    def cases(self) -> Mapping[str, Mapping[str, Any]]:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
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
            msg = f"benchmark operations must be positive, got {operations}"
            raise ValueError(msg)
        sample_values, observed = _counter_observation(name, samples)

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
        return _compare_counter(name, expected, sample_values, observed)

    def observe_counter_slope(
        self,
        name: str,
        *,
        unit: str,
        small_operations: int,
        large_operations: int,
        small_samples: Sequence[int],
        large_samples: Sequence[int],
    ) -> int:
        """Record or compare inference growth between two workload sizes."""
        small_values, large_values, observed = _counter_slope_observation(
            name,
            small_operations,
            large_operations,
            small_samples,
            large_samples,
        )
        case = _counter_slope_case(self._document, name, unit)
        if self.update:
            case["inference_slope"] = {
                "small_operations": small_operations,
                "large_operations": large_operations,
                "delta_inferences": observed,
            }
            return observed
        return _compare_counter_slope(
            name,
            case.get("inference_slope"),
            small_operations=small_operations,
            large_operations=large_operations,
            small_values=small_values,
            large_values=large_values,
            observed=observed,
        )

    def remove_case(self, name: str) -> None:
        """Drop a pinned case during an update, for rows nothing measures.

        A pinned row no measurement reaches can never fail, so it survives
        renames and lost artifacts as a dead receipt; pruning is part of
        re-pinning and is therefore update-only.
        """
        if not self.update:
            msg = f"remove_case({name!r}) outside update mode"
            raise AssertionError(msg)
        if name not in self._document["benchmarks"]:
            msg = f"benchmark baseline has no case named {name!r}"
            raise KeyError(msg)
        del self._document["benchmarks"][name]

    def observe_configuration(
        self, live: Mapping[str, Any], *, stamp: bool | None = None
    ) -> None:
        """Stamp or verify the measurement configuration the counters ran in.

        Deterministic counters only compare within one configuration: the C
        reader's presence moved file-load 8704891 to 722264 with zero code
        change, so a tree measuring in one mode against pins from the other
        produces confounded verdicts. Update mode stamps the live
        configuration; comparison mode refuses a missing or differing stamp.

        ``stamp=False`` makes even an update verify-only: a runner that
        re-measures a SUBSET of the document (the instruction checker) must
        not rewrite the fingerprint the other pins were measured under, so
        it verifies when a stamp exists and leaves an absent stamp to the
        owning full-battery updater.
        """
        if stamp is None:
            stamp = self.update
        if self.update and stamp:
            self._document["counter_configuration"] = dict(live)
            return
        stored = self._document.get("counter_configuration")
        if stored is None and self.update:
            return
        if stored is None:
            msg = (
                f"benchmark baseline carries no counter_configuration stamp; "
                f"live configuration is {dict(live)!r}: re-pin with "
                f"--update-baseline so comparisons declare their configuration"
            )
            raise AssertionError(msg)
        if stored != dict(live):
            msg = (
                f"counter configuration drift: baseline pinned under "
                f"{stored!r} but this run measures under {dict(live)!r}; "
                f"restore the pinned configuration (build the artifact or "
                f"unset the mode override) or re-pin with --update-baseline"
            )
            raise AssertionError(msg)

    def validate_case(self, name: str, *, unit: str, operations: int) -> None:
        """Check metadata when a wall-only run deliberately skips counters."""
        if operations <= 0:
            msg = f"benchmark operations must be positive, got {operations}"
            raise ValueError(msg)
        self._case(name, unit=unit, operations=operations)

    def observe_wall(self, name: str, seconds_per_operation: float) -> None:
        """Record wall time or retain it as advisory comparison metadata."""
        if seconds_per_operation <= 0:
            msg = "benchmark wall time must be positive"
            raise ValueError(msg)
        case = self._document["benchmarks"].get(name)
        if case is None:
            msg = f"benchmark {name!r} has no counter observation"
            raise KeyError(msg)
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
        observed = _instruction_observation(name, samples, noise_percent)
        if self.update:
            case = self._document["benchmarks"].get(name)
            if case is None:
                msg = f"benchmark {name!r} has no wall/counter baseline"
                raise KeyError(msg)
            case["instructions"] = observed
            case["instruction_noise_percent"] = noise_percent
            return observed

        case = self._document["benchmarks"].get(name)
        if case is None:
            msg = f"benchmark baseline has no case named {name!r}"
            raise AssertionError(msg)
        return _compare_instructions(name, case, samples, observed)

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
            msg = f"benchmark baseline has no case named {name!r}; regenerate it explicitly"
            raise AssertionError(
                msg
            )
        if case.get("unit") != unit:
            msg = f"{name} unit changed from {case.get('unit')!r} to {unit!r}"
            raise AssertionError(msg)
        if case.get("operations") != operations:
            msg = f"{name} operation count changed from {case.get('operations')!r} to {operations}"
            raise AssertionError(
                msg
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
            msg = f"{name} completed {completed} {unit}, expected {operations}"
            raise AssertionError(msg)
        return completed

    samples: list[int] | None = None
    if engine is not None and baseline.compare_counters:
        samples = _counter_samples(
            checked,
            operations=operations,
            setup=setup,
            teardown=teardown,
            engine=engine,
        )

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


def benchmark_counter_slope(
    baseline: BenchmarkBaseline,
    *,
    name: str,
    unit: str,
    small_operations: int,
    small_operation: Callable[[Any], int],
    large_operations: int,
    large_operation: Callable[[Any], int],
    setup: Callable[[], Any],
    teardown: Callable[[Any], None],
    engine: Callable[[Any], Any],
) -> int | None:
    """Gate inference growth between two fixed workload sizes."""
    if not baseline.compare_counters:
        return None
    small_samples = _counter_samples(
        small_operation,
        operations=small_operations,
        setup=setup,
        teardown=teardown,
        engine=engine,
    )
    large_samples = _counter_samples(
        large_operation,
        operations=large_operations,
        setup=setup,
        teardown=teardown,
        engine=engine,
    )
    return baseline.observe_counter_slope(
        name,
        unit=unit,
        small_operations=small_operations,
        large_operations=large_operations,
        small_samples=small_samples,
        large_samples=large_samples,
    )


def _instruction_request(
    command: Sequence[str],
    rounds: int,
    timeout: float,
) -> tuple[str, float]:
    if rounds < _COUNTER_SAMPLES:
        msg = f"instruction measurement needs at least {_COUNTER_SAMPLES} rounds"
        raise ValueError(msg)
    if not command:
        msg = "instruction measurement command cannot be empty"
        raise ValueError(msg)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        msg = f"instruction measurement timeout must be positive, got {timeout!r}"
        raise ValueError(msg)
    perf = shutil.which("perf")
    if perf is None:
        msg = "perf is required to measure instructions:u"
        raise FileNotFoundError(msg)
    if not os.access("/usr/bin/setarch", os.X_OK):
        msg = "setarch is required to measure instructions:u reproducibly"
        raise FileNotFoundError(
            msg
        )
    return perf, float(timeout)


def _parse_instruction_sample(returncode: int, stdout: str, stderr: str) -> int:
    if returncode != 0:
        detail = stderr.strip() or stdout.strip()
        msg = f"perf stat failed with exit {returncode}: {detail}"
        raise RuntimeError(msg)
    fields = [
        line.split(",", 1)[0] for line in stderr.splitlines() if ",instructions:u," in line
    ]
    if len(fields) != 1 or not fields[0].isdigit():
        msg = f"perf stat did not return one numeric instructions:u counter: {stderr.strip()}"
        raise RuntimeError(
            msg
        )
    return int(fields[0])


def measure_instructions(
    command: Sequence[str],
    *,
    rounds: int = _COUNTER_SAMPLES,
    controlled: bool = False,
    timeout: float = 60.0,
) -> tuple[int, ...]:
    """Run command under perf stat and return retired instructions per run."""
    perf, timeout = _instruction_request(command, rounds, timeout)
    #The child environment is BUILT, not inherited, for two measured reasons.
    #PYTHONHASHSEED pinned: per-launch hash randomization moves a dict-heavy
    #workload's retired-instruction count by more than the gate's whole noise
    #allowance (json-wire spread 1.46% across four launches, 0.098% with the
    #seed pinned [measured 2026-08-17]), and a security feature has no place
    #in a reproducibility harness. The allowlist: the SIZE of the environment
    #block moves where the process heap starts, which selects how many times
    #the engine's global stack grows mid-measurement; source-load measured a
    #stable 957.6M instructions under check.sh's environment against a stable
    #low mode under a bare shell, three samples each within 0.002%, inference
    #counter identical [measured 2026-08-17]. A fixed environment makes the
    #measurement caller-independent without touching the engine's own stack
    #economics (presizing stacks instead cost save-load-metta +2.35%).
    environment = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "LD_LIBRARY_PATH", "SWI_HOME_DIR")
        if name in os.environ
    } | {"LC_ALL": "C", "PYTHONHASHSEED": "0"}
    samples: list[int] = []
    for _ in range(rounds):
        returncode, stdout, stderr = _run_perf(
            perf,
            command,
            environment,
            controlled=controlled,
            timeout=timeout,
        )
        samples.append(_parse_instruction_sample(returncode, stdout, stderr))
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
                os.set_inheritable(descriptor, True)  # noqa: FBT003  -- os.set_inheritable is positional-only and the literal states the requested descriptor state
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
        #setarch -R disables address-space randomization for the child tree:
        #with the environment and hash seed already pinned, the residual
        #spread (json-wire 0.3% across a triple) tracks the kernel moving
        #the heap and stack bases per launch, which selects the same
        #alignment modes the environment block does. ASLR is the third
        #security feature with no place in a reproducibility harness.
        argv = [
            "/usr/bin/setarch",
            "-R",
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
                argv[0],
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
                    msg = f"perf stat exceeded its {timeout:g} second limit"
                    raise TimeoutError(msg)  # noqa: TRY301  -- the raise stays inside this rollback boundary so the same handler records the failure
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
    "benchmark_counter_slope",
    "count_atoms",
    "measure_instructions",
]
