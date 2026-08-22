"""Purpose: verify memory/scale fitting, pin comparison, and process isolation.

Guarantees:
  - raw repetitions survive aggregation with their full observed band.
  - linear and quadratic synthetic curves are classified by their intended
    complexity families.
  - the CLI quick lane executes each point in a distinct spawned process.
  - controlled projection workloads check both shared and distinct-column
    answer shapes before they can publish an instruction sample
    [tested: test_instruction_join_workload_checks_both_projection_shapes;
    commit=ed2f4ffeb55dd524a87e35aac078094924b6994b].
  - the streaming answer curve measures bounded cursor memory without unique
    wire names populating the separately measured intern caches.
"""

import json

from bench import main as benchmark_main
from benchmarks.memory_scale import (
    CASES,
    aggregate_samples,
    baseline_document,
    compare_baseline,
    fit_curve,
)
from benchmarks.pure import main as pure_benchmark_main


def test_curve_fit_distinguishes_linear_and_quadratic_growth():  # noqa: D103 -- pytest discovers this descriptive contract test
    sizes = [10, 100, 1_000, 10_000]
    linear = fit_curve(sizes, [71, 611, 6_011, 60_011])
    quadratic = fit_curve(sizes, [103, 10_003, 1_000_003, 100_000_003])

    assert linear["best_model"] == "linear"
    assert linear["models"]["linear"]["nrms"] < 1e-9
    assert quadratic["best_model"] == "quadratic"
    assert quadratic["models"]["quadratic"]["nrms"] < 1e-9


def test_curve_fit_recognises_a_bounded_linear_cache():  # noqa: D103 -- pytest discovers this descriptive contract test
    sizes = [100, 1_000, 10_000, 100_000]
    entries = [100, 1_000, 10_000, 65_536]

    fitted = fit_curve(sizes, entries)

    assert fitted["best_model"] == "capped_linear"
    assert fitted["models"]["capped_linear"]["nrms"] < 1e-9


def test_aggregation_preserves_samples_and_noise_band():  # noqa: D103 -- pytest discovers this descriptive contract test
    case = CASES["join-shared"]
    raw = {
        1: [
            {"inferences": 10, "_worker_pid": 101},
            {"inferences": 12, "_worker_pid": 102},
        ],
        10: [
            {"inferences": 100, "_worker_pid": 103},
            {"inferences": 105, "_worker_pid": 104},
        ],
        100: [
            {"inferences": 1_000, "_worker_pid": 105},
            {"inferences": 1_003, "_worker_pid": 106},
        ],
    }

    result = aggregate_samples(case, raw)

    metric = result["metrics"]["inferences"]
    assert metric["samples"] == {
        "1": [10, 12],
        "10": [100, 105],
        "100": [1_000, 1_003],
    }
    assert metric["representative"] == [10, 100, 1_000]
    assert metric["noise"]["absolute_max"] == 5
    assert result["worker_pids"]["10"] == [103, 104]


def test_aggregation_accepts_controlled_instruction_samples():  # noqa: D103 -- pytest discovers this descriptive contract test
    case = CASES["join-projection"]
    raw = {
        size: [{"inferences": size, "_worker_pid": size}]
        for size in case.sizes
    }
    instructions = {
        size: [size * 100, size * 101, size * 102] for size in case.sizes
    }

    result = aggregate_samples(
        case,
        raw,
        extra_metrics={"instructions": instructions},
    )

    assert result["primary_metric"] == "instructions"
    assert result["metrics"]["instructions"]["representative"] == [
        size * 100 for size in case.sizes
    ]


def test_instruction_join_workload_checks_both_projection_shapes():  # noqa: D103 -- pytest discovers this descriptive contract test
    assert pure_benchmark_main(["memory-join-shared", "--size", "10"]) == 0
    assert pure_benchmark_main(["memory-join-projection", "--size", "10"]) == 0


def test_baseline_comparison_uses_pinned_noise_and_names_a_regression():  # noqa: D103 -- pytest discovers this descriptive contract test
    case = CASES["join-shared"]
    raw = {
        size: [{"inferences": size * 10, "_worker_pid": size}]
        for size in case.sizes
    }
    result = {
        "schema": 1,
        "repetitions": 1,
        "cases": {case.name: aggregate_samples(case, raw)},
    }
    baseline = baseline_document(result, cause_commit="a" * 40)

    assert compare_baseline(result, baseline) == []
    moved = json.loads(json.dumps(result))
    moved["cases"][case.name]["metrics"]["inferences"]["representative"][-1] *= 2
    failures = compare_baseline(moved, baseline)
    assert len(failures) == 1
    assert "moved" in failures[0]

    baseline["cases"]["unselected"] = baseline["cases"][case.name]
    assert compare_baseline(result, baseline, names=[case.name]) == []


def test_memory_scale_cli_runs_fresh_workers(tmp_path):  # noqa: D103 -- pytest discovers this descriptive contract test
    output = tmp_path / "memory.json"

    assert benchmark_main(
        [
            "--memory-scale",
            "--memory-quick",
            "--memory-repetitions",
            "1",
            "--timeout",
            "60",
            "--json",
            str(output),
            "stored-atoms-native",
        ]
    ) == 0

    document = json.loads(output.read_text(encoding="utf-8"))
    result = document["cases"]["stored-atoms-native"]
    assert result["sizes"] == [10, 100]
    pids = [pid for samples in result["worker_pids"].values() for pid in samples]
    assert len(pids) == len(set(pids)) == 2
    assert result["metrics"]["storage_module_bytes"]["representative"][1] > 0


def test_stream_curve_excludes_wire_cache_growth(tmp_path):  # noqa: D103 -- pytest discovers this descriptive contract test
    output = tmp_path / "stream.json"

    assert benchmark_main(
        [
            "--memory-scale",
            "--memory-quick",
            "--memory-repetitions",
            "1",
            "--timeout",
            "60",
            "--json",
            str(output),
            "query-stream",
        ]
    ) == 0

    result = json.loads(output.read_text(encoding="utf-8"))["cases"]["query-stream"]
    peak = result["metrics"]["python_peak_bytes"]
    assert result["primary_metric"] == "python_peak_bytes"
    assert result["expected"] == "constant"
    assert peak["fit"]["models"]["constant"]["nrms"] < 0.10


def test_memory_scale_cli_gates_object_reclamation(tmp_path):  # noqa: D103 -- pytest discovers this descriptive contract test
    output = tmp_path / "objects.json"

    assert benchmark_main(
        [
            "--memory-scale",
            "--memory-quick",
            "--memory-repetitions",
            "1",
            "--timeout",
            "60",
            "--json",
            str(output),
            "object-reclamation",
        ]
    ) == 0

    result = json.loads(output.read_text(encoding="utf-8"))["cases"][
        "object-reclamation"
    ]
    assert result["metrics"]["loaded_box_entries"]["representative"] == [1, 10]
    assert result["metrics"]["post_drop_box_entries"]["representative"] == [0, 0]
    assert result["metrics"]["post_drop_live_objects"]["representative"] == [0, 0]
