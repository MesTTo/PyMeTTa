"""Purpose: run selected pytest-benchmark cases with committed baselines.
Guarantees:
  - every named case runs in a fresh process, so global engine state cannot
    make subset and suite counters disagree [tested
    test_benchmark_cli_spawns_each_case]
  - unknown names fail through argparse and --list reports every case
    [tested test_benchmark_cli_lists_and_rejects_case_names]
Owns:
  - main joins each benchmark process and terminates one that exceeds its
    explicit limit [tested test_benchmark_cli_spawns_each_case]
  - JSON output is assembled in a temporary directory and atomically
    replaces its destination [tested test_benchmark_json_merge_is_atomic]
  - updating selected cases preserves every unselected committed case
    [tested test_benchmark_json_merge_preserves_unselected_cases]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

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
    "direct-join": "test_direct_join",
    "eval-arith": "test_eval_arithmetic",
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
    "term-operators": "test_term_operators",
    "weighted-relation": "test_weighted_relation",
    "wire-codec": "test_wire_codec",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--list", action="store_true", dest="list_cases")
    parser.add_argument("--counter-only", action="store_true")
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


def _run_case(pytest_arguments: list[str], update: bool) -> None:
    os.environ["PETTA_BENCHMARK_COUNTERS"] = "1"
    os.environ["PETTA_UPDATE_BENCHMARK_BASELINE"] = "1" if update else "0"
    result = pytest.main(pytest_arguments)
    if result:
        raise SystemExit(int(result))


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


def _write_merged_json(paths: Sequence[Path], target: Path) -> None:
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if not documents:
        raise ValueError("cannot write an empty benchmark JSON document")
    for path, document in zip(paths, documents, strict=True):
        if not isinstance(document, dict) or not isinstance(document.get("benchmarks"), list):
            raise ValueError(f"benchmark JSON has invalid structure: {path}")
        if len(document["benchmarks"]) != 1:
            raise ValueError(f"benchmark JSON must hold exactly one case: {path}")
        if document.get("machine_info") != documents[0].get("machine_info"):
            raise ValueError(f"benchmark JSON machine metadata changed: {path}")
        if document.get("commit_info") != documents[0].get("commit_info"):
            raise ValueError(f"benchmark JSON commit metadata changed: {path}")
    merged: dict[str, Any] = documents[0]
    updated = {
        benchmark["name"]: benchmark
        for document in documents
        for benchmark in document.get("benchmarks", [])
    }
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or not isinstance(existing.get("benchmarks"), list):
            raise ValueError(f"benchmark JSON has invalid structure: {target}")
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested benchmark cases through isolated pytest processes."""
    parser = _parser()
    arguments = parser.parse_args(argv)
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
        name for name in (arguments.names or sorted(CASES))
        if name not in set(arguments.skip)
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
    with tempfile.TemporaryDirectory(prefix="petta-benchmark-json-") as temporary:
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
                    arguments.update_baseline,
                ),
                name=f"petta-benchmark-{name}",
            )
            process.start()
            process.join(arguments.timeout)
            if process.is_alive():
                process.terminate()
                process.join(5.0)
                if process.is_alive():
                    process.kill()
                    process.join()
                message = (
                    f"benchmark {name} exceeded its {arguments.timeout:g} second limit"
                )
                if not arguments.keep_going:
                    raise TimeoutError(message)
                failures.append(message)
                continue
            if process.exitcode != 0:
                message = (
                    f"benchmark {name} process exited with status {process.exitcode}"
                )
                if not arguments.keep_going:
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
