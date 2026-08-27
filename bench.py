"""Purpose: run selected pytest-benchmark cases with committed baselines.
Guarantees:
  - every named case runs in a fresh process, so global engine state cannot
    make subset and suite counters disagree [tested
    test_benchmark_cli_spawns_each_case; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - unknown names fail through argparse and --list reports every case
    [tested: test_benchmark_cli_lists_and_rejects_case_names; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - --memory-scale composes the same spawned-process timeout and cleanup
    discipline with structural, Python-allocation, and Linux process-memory
    curves [tested: test_memory_scale_cli_runs_fresh_workers; commit=d843bb6d17a525c36afd21cab077d63b34447535]
Owns resources:
  - main joins each benchmark process and terminates one that exceeds its
    explicit limit [tested: test_benchmark_cli_spawns_each_case; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - JSON output is assembled in a temporary directory and atomically
    replaces its destination
    [tested: test_benchmark_json_merge_is_atomic; commit=dcfc20be4933c19140ccb5759291401d13058301]
  - updating selected cases preserves every unselected committed case
    [tested: test_benchmark_json_merge_preserves_unselected_cases; commit=dcfc20be4933c19140ccb5759291401d13058301]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

CASES = {
    "add-batch": "test_add_batch",
    "add-single": "test_add_single",
    "add-table-rows": "test_add_table_rows",
    "alpha-unique": "test_alpha_unique",
    "automatic-tabling": "test_automatic_tabling_growth",
    "direct-join": "test_direct_join",
    "eval-arith": "test_eval_arithmetic",
    "file-load": "test_file_load",
    "json-wire": "test_json_wire",
    "let-heavy": "test_let_heavy",
    "loop-1m": "test_loop_million",
    "op-encoded": "test_encoded_operation",
    "op-raw": "test_raw_operation",
    "prepared-join": "test_prepared_join",
    "py-method-call": "test_py_method_call",
    "query-2k-rows": "test_query_rows",
    "query-limit-guarded": "test_query_limit_guarded",
    "query-limit-plain": "test_query_limit_plain",
    "query-where": "test_query_where",
    "register-op": "test_register_operation",
    "run-source": "test_run_source",
    "save-load-fast": "test_save_load_fast",
    "save-load-metta": "test_save_load_metta",
    "sort-atom": "test_sort_atom",
    "source-load": "test_source_load",
    "space-digest": "test_space_digest",
    "space-name": "test_space_name",
    "subscribe-tax": "test_subscription_tax",
    "foreign-match": "test_foreign_match",
    "handle-round-trip": "test_handle_round_trip",
    "table-bridge-match": "test_table_bridge_match",
    "typed-call": "test_typed_call",
    "term-operators": "test_term_operators",
    "annotated-relation": "test_annotated_relation",
    "wire-codec": "test_wire_codec",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--list", action="store_true", dest="list_cases")
    parser.add_argument("--counter-only", action="store_true")
    parser.add_argument(
        "--memory-scale",
        action="store_true",
        help="run memory and scaling curves instead of pytest benchmark cases",
    )
    parser.add_argument("--memory-repetitions", type=int, default=3)
    parser.add_argument("--memory-quick", action="store_true")
    parser.add_argument("--memory-cause-commit", default=os.environ.get("METTA_MEMORY_CAUSE_COMMIT", "WORKTREE"))
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--compare-wall", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        metavar="NAME",
        help="omit this benchmark; repeatable",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="run every selected case and report all failures at the end, "
        "instead of stopping at the first",
    )
    return parser


def _run_case(pytest_arguments: list[str], *, update: bool) -> None:
    os.environ["METTA_BENCHMARK_COUNTERS"] = "1"
    os.environ["METTA_UPDATE_BENCHMARK_BASELINE"] = "1" if update else "0"
    result = pytest.main(pytest_arguments)
    if result:
        raise SystemExit(int(result))


def finish_process(process: Any, timeout: float) -> str | None:
    """Join one spawned worker and reap it on every timeout path."""
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        if process.is_alive():
            process.kill()
            process.join()
        return f"process exceeded its {timeout:g} second limit"
    if process.exitcode != 0:
        return f"process exited with status {process.exitcode}"
    return None


def _arguments_for(
    name: str,
    *,
    directory: Path,
    counter_only: bool,
    compare_wall: bool,
    json_path: Path | None,
) -> list[str]:
    benchmark_file = directory / "benchmarks" / "test_benchmarks.py"
    arguments = [
        f"{benchmark_file}::{CASES[name]}",
        "-q",
        f"--rootdir={directory}",
        "-c",
        str(directory / "pyproject.toml"),
    ]
    if counter_only:
        arguments.append("--benchmark-disable")
    if compare_wall:
        arguments.append(f"--benchmark-compare={directory / 'benchmarks' / 'pytest-baseline.json'}")
    if json_path is not None:
        arguments.append(f"--benchmark-json={json_path}")
    return arguments


def _benchmark_documents(paths: Sequence[Path]) -> list[dict[str, Any]]:
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if not documents:
        msg = "cannot write an empty benchmark JSON document"
        raise ValueError(msg)
    for path, document in zip(paths, documents, strict=True):
        if not isinstance(document, dict) or not isinstance(document.get("benchmarks"), list):
            msg = f"benchmark JSON has invalid structure: {path}"
            raise ValueError(msg)  # noqa: TRY004  -- malformed serialized or configured content is a ValueError even when its runtime type reveals it
        if len(document["benchmarks"]) != 1:
            msg = f"benchmark JSON must hold exactly one case: {path}"
            raise ValueError(msg)
        if document.get("machine_info") != documents[0].get("machine_info"):
            msg = f"benchmark JSON machine metadata changed: {path}"
            raise ValueError(msg)
        if document.get("commit_info") != documents[0].get("commit_info"):
            msg = f"benchmark JSON commit metadata changed: {path}"
            raise ValueError(msg)
    return documents


def _write_merged_json(paths: Sequence[Path], target: Path) -> None:
    documents = _benchmark_documents(paths)
    merged: dict[str, Any] = documents[0]
    updated = {
        benchmark["name"]: benchmark
        for document in documents
        for benchmark in document.get("benchmarks", [])
    }
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or not isinstance(existing.get("benchmarks"), list):
            msg = f"benchmark JSON has invalid structure: {target}"
            raise ValueError(msg)
        for benchmark in existing["benchmarks"]:
            updated.setdefault(benchmark["name"], benchmark)
    merged["benchmarks"] = [updated[name] for name in sorted(updated)]
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, indent=4)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(target)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:  # noqa: C901  -- main keeps the child-process timeout and cleanup together so its branches share one state
    """Run the requested benchmark cases through isolated pytest processes."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.memory_repetitions < 1:
        parser.error("--memory-repetitions must be positive")
    if arguments.memory_scale:
        from benchmarks.memory_scale import CASES as MEMORY_CASES  # noqa: PLC0415
        from benchmarks.memory_scale import run_suite  # noqa: PLC0415

        if arguments.list_cases:
            print("\n".join(sorted(MEMORY_CASES)))
            return 0
        unknown = sorted((set(arguments.names) | set(arguments.skip)) - MEMORY_CASES.keys())
        if unknown:
            parser.error(
                f"unknown memory-scale benchmark {', '.join(unknown)}; "
                "use --memory-scale --list for valid names"
            )
        selected = [
            name
            for name in (arguments.names or sorted(MEMORY_CASES))
            if name not in set(arguments.skip)
        ]
        if not selected:
            parser.error("every selected memory-scale benchmark was skipped")
        if arguments.skip:
            print(f"skipping {', '.join(sorted(set(arguments.skip)))}")
        directory = Path(__file__).resolve().parent
        return run_suite(
            names=selected,
            repetitions=arguments.memory_repetitions,
            timeout=arguments.timeout,
            quick=arguments.memory_quick,
            output=arguments.json,
            baseline_path=directory / "benchmarks" / "memory-scale-baseline.json",
            update_baseline=arguments.update_baseline,
            cause_commit=arguments.memory_cause_commit,
            keep_going=arguments.keep_going,
            context=multiprocessing.get_context("spawn"),
            finish_process=finish_process,
        )
    if arguments.list_cases:
        print("\n".join(sorted(CASES)))
        return 0
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")

    unknown = sorted((set(arguments.names) | set(arguments.skip)) - CASES.keys())
    if unknown:
        parser.error(f"unknown benchmark {', '.join(unknown)}; use --list for valid names")

    directory = Path(__file__).resolve().parent
    selected = [
        name for name in (arguments.names or sorted(CASES)) if name not in set(arguments.skip)
    ]
    if not selected:
        parser.error("every selected benchmark was skipped")
    # A skip is a hole in the evidence, so say so rather than let a green run
    # read as full coverage.
    if arguments.skip:
        print(f"skipping {', '.join(sorted(set(arguments.skip)))}")
    json_target = arguments.json
    if arguments.update_baseline and json_target is None and not arguments.counter_only:
        json_target = directory / "benchmarks" / "pytest-baseline.json"

    context = multiprocessing.get_context("spawn")
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="metta-benchmark-json-") as temporary:
        json_paths: list[Path] = []
        for index, name in enumerate(selected):
            json_path = Path(temporary) / f"{index:03d}-{name}.json" if json_target else None
            process = context.Process(
                target=_run_case,
                args=(
                    _arguments_for(
                        name,
                        directory=directory,
                        counter_only=arguments.counter_only,
                        compare_wall=arguments.compare_wall,
                        json_path=json_path,
                    ),
                ),
                kwargs={"update": arguments.update_baseline},
                name=f"metta-benchmark-{name}",
            )
            process.start()
            process_failure = finish_process(process, arguments.timeout)
            if process_failure is not None:
                message = f"benchmark {name} {process_failure}"
                if not arguments.keep_going:
                    if "exceeded" in process_failure:
                        raise TimeoutError(message)
                    raise RuntimeError(message)
                failures.append(message)
                continue
            if json_path is not None:
                json_paths.append(json_path)
        if json_target is not None:
            _write_merged_json(json_paths, json_target)
            print(f"wrote benchmark data to {json_target}")
    if failures:
        print(f"\n{len(failures)} of {len(selected)} benchmarks failed:")
        for message in failures:
            print(f"  {message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
