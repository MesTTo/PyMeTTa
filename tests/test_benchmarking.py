"""Purpose: verify reusable benchmark setup, counter, and perf plumbing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import json
import os
import signal
from types import SimpleNamespace

import pytest

from bench import CASES, _write_merged_json
from bench import main as benchmark_main
from benchmarks.check_instructions import _CASES as INSTRUCTION_CASES
from benchmarks.conftest import pytest_benchmark_update_machine_info
from benchmarks.engine_workloads import (
    alpha_unique_case,
    close_engine_case,
    digest_case,
    let_heavy,
    let_space,
    py_method_case,
    sort_atom_case,
    source_load_case,
    space_name_case,
)
from benchmarks.pure import _CASES as PERF_CASES
from benchmarks.pure import _acknowledge
from benchmarks.pure import main as perf_workload_main
from benchmarks.subscription import (
    close_subscription_case,
    subscription_dispatch_case,
)
from benchmarks.workloads import json_payload, json_wire, term_operators, wire_atom, wire_codec
from petta import S
from petta.benchmarking import _run_perf
from petta.testing import (
    BenchmarkBaseline,
    benchmark_case,
    benchmark_counter_slope,
    count_atoms,
    measure_instructions,
)


class _Stats:
    def __init__(self, inferences):
        self.inferences = inferences

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _Engine:
    def __init__(self, inferences):
        self.inferences = inferences

    def stats(self):
        return _Stats(self.inferences)


class _MutableStats:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @property
    def inferences(self):
        return self.state.inferences


class _Benchmark:
    def __init__(self):
        self.extra_info = {}
        self.stats = None

    def pedantic(
        self,
        target,
        *,
        setup,
        teardown,
        rounds,
        warmup_rounds,
    ):
        result = None
        for _ in range(rounds + warmup_rounds):
            args, kwargs = setup()
            result = target(*args, **kwargs)
            teardown(*args, **kwargs)
        self.stats = SimpleNamespace(stats=SimpleNamespace(min=1.0))
        return result


class _DisabledBenchmark(_Benchmark):
    def pedantic(self, target, *, setup, teardown, **_options):
        args, kwargs = setup()
        try:
            return target(*args, **kwargs)
        finally:
            teardown(*args, **kwargs)


def test_benchmark_case_uses_fresh_state(tmp_path):
    baseline = BenchmarkBaseline(tmp_path / "baseline.json", update=True)
    created = []
    reaped = []

    def setup():
        state = SimpleNamespace(serial=len(created), engine=_Engine(7))
        created.append(state)
        return state

    fixture = _Benchmark()
    benchmark_case(
        fixture,
        baseline,
        name="fresh",
        unit="items",
        operations=1,
        operation=lambda _state: 1,
        setup=setup,
        teardown=reaped.append,
        engine=lambda state: state.engine,
        rounds=2,
        warmup_rounds=1,
    )

    assert len(created) == 6
    assert reaped == created
    assert fixture.extra_info["inference_samples"] == [7, 7, 7]


def test_benchmark_case_runs_with_wall_timing_disabled(tmp_path):
    baseline = BenchmarkBaseline(tmp_path / "baseline.json", update=True)
    fixture = _DisabledBenchmark()

    assert (
        benchmark_case(
            fixture,
            baseline,
            name="counter-only",
            unit="items",
            operations=1,
            operation=lambda _state: 1,
            setup=lambda: SimpleNamespace(engine=_Engine(4)),
            teardown=lambda _state: None,
            engine=lambda state: state.engine,
        )
        == 1
    )
    assert "wall_seconds_per_operation" not in fixture.extra_info


def test_baseline_rejects_inference_regressions_and_accepts_improvements(tmp_path):
    path = tmp_path / "baseline.json"
    updating = BenchmarkBaseline(path, update=True)
    updating.observe_counter("engine", unit="answers", operations=2, samples=[10, 10, 10])
    updating.observe_wall("engine", 0.25)
    updating.finish()

    baseline = BenchmarkBaseline(path)
    assert baseline.observe_counter("engine", unit="answers", operations=2, samples=[9, 9, 9]) == 9
    # A shift inside the absolute allowance is measurement artifact, not work:
    # the committed +2 join phantom does not scale with the workload and is
    # produced by predicates the benchmark never calls.
    assert (
        baseline.observe_counter("engine", unit="answers", operations=2, samples=[14, 14, 14])
        == 14
    )
    with pytest.raises(AssertionError, match="inference regression"):
        baseline.observe_counter("engine", unit="answers", operations=2, samples=[15, 15, 15])


def test_baseline_update_is_atomic_json(tmp_path):
    path = tmp_path / "baseline.json"
    baseline = BenchmarkBaseline(path, update=True)
    baseline.observe_counter("pure", unit="terms", operations=3, samples=None)
    baseline.observe_wall("pure", 0.5)
    baseline.finish()

    document = json.loads(path.read_text())
    assert document["benchmarks"]["pure"] == {
        "inferences": None,
        "operations": 3,
        "unit": "terms",
        "wall_seconds_per_operation": 0.5,
    }
    assert list(tmp_path.glob(".baseline.json.*")) == []


def test_benchmark_counter_slope_uses_fresh_state_and_gates_growth(tmp_path):
    path = tmp_path / "baseline.json"
    baseline = BenchmarkBaseline(path, update=True)
    baseline.observe_counter("growth", unit="rows", operations=8, samples=[30, 30, 30])
    created = []
    reaped = []

    def setup():
        state = SimpleNamespace(inferences=0)
        created.append(state)
        return state

    def operation(completed, inferences):
        def run(state):
            state.inferences = inferences
            return completed

        return run

    assert (
        benchmark_counter_slope(
            baseline,
            name="growth",
            unit="rows",
            small_operations=2,
            small_operation=operation(2, 11),
            large_operations=8,
            large_operation=operation(8, 35),
            setup=setup,
            teardown=reaped.append,
            engine=lambda state: SimpleNamespace(stats=lambda: _MutableStats(state)),
        )
        == 24
    )
    baseline.finish()

    assert len(created) == 6
    assert reaped == created
    assert json.loads(path.read_text())["benchmarks"]["growth"]["inference_slope"] == {
        "delta_inferences": 24,
        "large_operations": 8,
        "small_operations": 2,
    }

    comparison = BenchmarkBaseline(path)
    assert (
        comparison.observe_counter_slope(
            "growth",
            unit="rows",
            small_operations=2,
            large_operations=8,
            small_samples=[11, 11, 11],
            large_samples=[39, 39, 39],
        )
        == 28
    )
    with pytest.raises(AssertionError, match="inference slope regression"):
        comparison.observe_counter_slope(
            "growth",
            unit="rows",
            small_operations=2,
            large_operations=8,
            small_samples=[11, 11, 11],
            large_samples=[40, 40, 40],
        )


def test_measure_instructions_parses_perf_csv(monkeypatch):
    calls = []

    def run(executable, command, environment, *, controlled, timeout):
        calls.append((executable, command, environment, controlled, timeout))
        return 0, "", "12345,,instructions:u,1000,100.00,,\n"

    monkeypatch.setattr("petta.benchmarking._run_perf", run)
    assert measure_instructions(["python", "work.py"]) == (12345, 12345, 12345)
    assert all(
        call[1] == ["python", "work.py"] and not call[3] and call[4] == 60.0 for call in calls
    )


def test_perf_timeout_kills_and_reaps_process_group(monkeypatch):
    waits = []
    killed = []

    monkeypatch.setattr("petta.benchmarking.os.posix_spawn", lambda *_args, **_kwargs: 42)

    def waitpid(process, options):
        waits.append((process, options))
        return (0, 0) if options == os.WNOHANG else (process, signal.SIGKILL)

    ticks = iter([0.0, 2.0])
    monkeypatch.setattr("petta.benchmarking.os.waitpid", waitpid)
    monkeypatch.setattr("petta.benchmarking.os.killpg", lambda *args: killed.append(args))
    monkeypatch.setattr("petta.benchmarking.time.monotonic", lambda: next(ticks))

    with pytest.raises(TimeoutError, match="1 second limit"):
        _run_perf("/usr/bin/perf", ["python"], {}, controlled=False, timeout=1.0)
    assert killed == [(42, signal.SIGKILL)]
    assert waits == [(42, os.WNOHANG), (42, 0)]


def test_perf_acknowledgement_accepts_the_native_nul_terminator():
    reader, writer = os.pipe()
    try:
        os.write(writer, b"ack\n\0")
        _acknowledge(reader)
    finally:
        os.close(reader)
        os.close(writer)


def test_perf_workload_setup_and_teardown_stay_outside_control(monkeypatch):
    events = []

    def factory():
        events.append("setup")

        def operation():
            events.append("operation")
            return 1

        return operation, lambda: events.append("teardown")

    def controlled(operation):
        events.append("enable")
        result = operation()
        events.append("disable")
        return result

    monkeypatch.setitem(PERF_CASES, "probe", factory)
    monkeypatch.setattr("benchmarks.pure._controlled", controlled)

    assert perf_workload_main(["probe", "--controlled"]) == 0
    assert events == ["setup", "enable", "operation", "disable", "teardown"]


def test_perf_workload_teardown_runs_after_failure(monkeypatch):
    events = []

    def factory():
        def operation():
            events.append("operation")
            msg = "workload failed"
            raise LookupError(msg)

        return operation, lambda: events.append("teardown")

    monkeypatch.setitem(PERF_CASES, "failing-probe", factory)

    with pytest.raises(LookupError, match="workload failed"):
        perf_workload_main(["failing-probe"])
    assert events == ["operation", "teardown"]


def test_count_atoms_derives_the_wire_workload_size():
    atom = S.deep(*(S.node(i, float(i), S.leaf) for i in range(50)))
    assert count_atoms(atom) == 252


def test_pure_workload_counts_are_derived():
    atom = wire_atom()
    assert wire_codec(atom, trips=2) == 2 * count_atoms(atom)
    assert json_wire(json_payload(), trips=2) == 2
    assert term_operators(terms=3) == 3


def test_instruction_inventory_covers_primitive_heavy_engine_paths():
    engine_cases = {
        "alpha-unique",
        "let-heavy",
        "py-method-call",
        "sort-atom",
        "source-load",
        "space-digest",
        "space-name",
    }
    assert engine_cases <= PERF_CASES.keys()
    assert set(INSTRUCTION_CASES) == PERF_CASES.keys()


@pytest.mark.parametrize(
    ("factory", "operations"),
    [
        (alpha_unique_case, 20),
        (digest_case, 20),
        (py_method_case, 3),
        (sort_atom_case, 20),
        (source_load_case, 5),
        (space_name_case, 3),
    ],
)
def test_primitive_workloads_check_public_results(factory, operations):
    state = factory(operations)
    try:
        assert state[1]() == operations
    finally:
        close_engine_case(state)


def test_let_workload_checks_its_bignum_result():
    space = let_space()
    try:
        assert let_heavy(space, 10) == 10
    finally:
        space.drop()


def test_benchmark_cli_lists_and_rejects_case_names(capsys):
    assert benchmark_main(["--list"]) == 0
    assert capsys.readouterr().out.splitlines() == sorted(CASES)
    with pytest.raises(SystemExit) as stopped:
        benchmark_main(["misspelled"])
    assert stopped.value.code == 2


def test_benchmark_cli_spawns_each_case(monkeypatch):
    processes = []

    class Process:
        exitcode = 0

        def __init__(self, **options):
            self.options = options
            self.joined = []
            processes.append(self)

        def start(self):
            return None

        def join(self, timeout=None):
            self.joined.append(timeout)

        def is_alive(self):
            return False

    context = SimpleNamespace(Process=Process)
    monkeypatch.setattr("bench.multiprocessing.get_context", lambda _method: context)

    assert benchmark_main(["add-batch", "add-single", "--counter-only"]) == 0
    assert [process.options["name"] for process in processes] == [
        "petta-benchmark-add-batch",
        "petta-benchmark-add-single",
    ]
    assert all(process.joined == [120.0] for process in processes)


def test_benchmark_json_merge_is_atomic(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    target = tmp_path / "merged.json"
    metadata = {"machine_info": {"cpu": "fixed"}, "commit_info": {"id": "abc"}}
    first.write_text(json.dumps({"benchmarks": [{"name": "first"}], "schema": 1} | metadata))
    second.write_text(json.dumps({"benchmarks": [{"name": "second"}], "schema": 1} | metadata))

    _write_merged_json([first, second], target)

    assert [item["name"] for item in json.loads(target.read_text())["benchmarks"]] == [
        "first",
        "second",
    ]
    assert list(tmp_path.glob(".merged.json.*")) == []


def test_benchmark_json_merge_preserves_unselected_cases(tmp_path):
    selected = tmp_path / "selected.json"
    target = tmp_path / "baseline.json"
    selected.write_text(
        json.dumps(
            {
                "benchmarks": [{"name": "selected", "stats": {"min": 1}}],
                "machine_info": {"cpu": "current"},
                "commit_info": {"id": "new"},
            }
        )
    )
    target.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {"name": "selected", "stats": {"min": 9}},
                    {"name": "untouched", "stats": {"min": 2}},
                ],
                "machine_info": {"cpu": "old"},
                "commit_info": {"id": "old"},
            }
        )
    )

    _write_merged_json([selected], target)

    document = json.loads(target.read_text())
    assert document["benchmarks"] == [
        {"name": "selected", "stats": {"min": 1}},
        {"name": "untouched", "stats": {"min": 2}},
    ]
    assert document["machine_info"] == {"cpu": "current"}
    assert document["commit_info"] == {"id": "new"}


def test_benchmark_machine_info_is_stable():
    machine_info = {
        "cpu": {
            "brand_raw": "processor",
            "hz_actual": [5_000_000_000, 0],
            "hz_actual_friendly": "5.0 GHz",
            "hz_advertised": [5_000_000_000, 0],
            "hz_advertised_friendly": "5.0 GHz",
        }
    }
    pytest_benchmark_update_machine_info(None, machine_info)
    assert machine_info == {"cpu": {"brand_raw": "processor"}}


def test_subscription_dispatch_case_measures_writes_only():
    """Building the subscriptions is setup, not the measurement.

    A thousand standing queries cost more to CREATE than two hundred writes
    cost to dispatch, so a window that held the construction would report
    the construction. This pins that the operation the case hands back does
    the writes and nothing else, and that the writes really are dispatched:
    one of the thousand matches each, so a run delivering nothing would be
    measuring an empty loop.
    """
    state = subscription_dispatch_case(subscriptions=20, writes=5)
    space, standing, delivered, run = state
    try:
        assert len(standing) == 20
        assert delivered[0] == 0, "construction delivered before the window"
        assert run() == 5
        assert delivered[0] == 5, "the measured writes dispatched nothing"
        assert space.count() == 5
    finally:
        close_subscription_case(state)
    assert all(not subscription._active for subscription in standing)


def test_the_benchmark_suite_prices_a_file_load():
    """P0.18: loader regressions used to land in no counter case, because
    `source-load` runs a string through the engine and the save-load pair
    prices a round trip whose baselines had drifted high. The `file-load`
    bench replace-loads a 20,001-atom file every round (withdrawal plus
    re-add plus content digest, the loader's whole path) and follows with
    an unchanged `import!`, the skip branch. This test pins the wiring:
    the registry row, the runner function, and a live integer baseline.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    registry = (root / "bindings" / "python" / "bench.py").read_text()
    assert '"file-load": "test_file_load"' in registry
    suite = (root / "bindings" / "python" / "benchmarks" / "test_benchmarks.py").read_text()
    assert "def test_file_load(" in suite
    data = json.loads(
        (root / "bindings" / "python" / "benchmarks" / "baseline.json").read_text()
    )
    entry = data["benchmarks"]["file-load"]
    assert isinstance(entry["inferences"], int) and entry["inferences"] > 0
