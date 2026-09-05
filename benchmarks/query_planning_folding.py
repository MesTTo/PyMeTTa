"""Purpose: measure complete public constant-planning workloads and both controls.

Run from the repository root in a separate process for each mode::

    PYTHONPATH=extensions/python $VENV/bin/python -m benchmarks.query_planning_folding \
        --mode optimized --metadata ai-tmp/folding-optimized-metadata.json

The controls disable constant folding, restore body-reading metadata consumers,
or combine those changes. The fixed-list fixture has a fixed head and result:
repeated scans and body copies cost O(q*n), while folding plus projected metadata
targets O(n+q), including preparation. Source length grows linearly with n in
both fixtures; arbitrary-precision arithmetic remains sensitive to bit sizes.

Guarantees:
  - registration, first compilation and q completed public calls are measured
    separately; every returned bag is checked before reporting its workload
    [tested: the three-mode complete size sweep; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - mismatched source fingerprints before and after a run reject its result
    [source: benchmarks.query_planning.finish_metadata and main in this file;
    commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
Owns resources: each MeTTa context closes after its workload; control predicate
  substitutions last for this process, and metadata uses finish_metadata.
Decides: samples must be a positive integer; the default is three. SWI ports omit
  work inside Python and native predicates, so process_time_ns records their
  process CPU too. Startup, source construction and diagnostics are excluded.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from time import process_time_ns
from typing import Any

from benchmarks.query_planning import finish_metadata, source_snapshot
from metta import MeTTa

_ROOT = Path(__file__).resolve().parents[3]


def _measure(
    m: MeTTa, operation: Callable[..., Any], *args: Any,
) -> tuple[Any, dict[str, int]]:
    started = process_time_ns()
    with m.stats() as stats:
        result = operation(*args)
    elapsed = process_time_ns() - started
    return result, {"inferences": stats.inferences, "process_cpu_ns": elapsed}


def _inspect_definition(m: MeTTa, name: str) -> dict[str, Any]:
    return m.runtime.must(
        "space_module(Space, _Module), "
        "( current_predicate(_Module:Function/1) -> Compiled = true ; Compiled = false ), "
        "( materialize:materialized_predicate(_Module, Function, 0, _) "
        "-> Materialized = true ; Materialized = false )",
        Space=m.self.name,
        Function=name,
    )


def _run_queries(m: MeTTa, call: str, expected: int, queries: int) -> None:
    for _ in range(queries):
        assert m.run(call) == [[expected]]


def _legacy_metadata_reads(m: MeTTa) -> None:
    # This control changes reads only. The production ownership tables and
    # mutation transactions remain intact, so lifecycle cleanup still applies.
    m.runtime.must(
        "assertz((translator:folding_measure_rewrite(_X, _X) :- var(_X), !)), "
        "assertz((translator:folding_measure_rewrite(fun_meta_head(_M, _F, _H), "
        "fun_meta_clause(_M, _F, _H, _)) :- !)), "
        "assertz((translator:folding_measure_rewrite(fun_meta_projection(_M, _F, _, _), "
        "fun_meta_clause(_M, _F, _, _)) :- !)), "
        "assertz((translator:folding_measure_rewrite(_X, _X) :- atomic(_X), !)), "
        "assertz((translator:folding_measure_rewrite(_X, _Y) :- "
        "_X =.. [_F|_Xs], maplist(translator:folding_measure_rewrite, _Xs, _Ys), "
        "_Y =.. [_F|_Ys])), "
        "forall(member(_Name/_Arity, [fun_meta_module/3, metta_function_translated/2, "
        "dispatch_head_covers/4, dispatch_any_head_matches/4, metta_equation_call/2, "
        "metta_segment_equation_in/3, declared_arity_misses_existing_equation/3, reduce/3]), "
        "(functor(_Head, _Name, _Arity), "
        "findall((_Head :- _Body), clause(translator:_Head, _Body), _Clauses), "
        "abolish(translator:_Name/_Arity), "
        "forall(member((_OldHead :- _OldBody), _Clauses), "
        "(translator:folding_measure_rewrite(_OldBody, _NewBody), "
        "assertz(translator:(_OldHead :- _NewBody))))))"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Write exact CPU/inference phases with checked bags and source fingerprints."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["optimized", "folding-control", "metadata-control", "combined-control"], required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3, metavar="N")
    args = parser.parse_args(argv)
    if args.samples < 1:
        parser.error("samples must be a positive integer")
    before = source_snapshot()
    git = shutil.which("git")
    if git is None:
        message = "git is required to record benchmark source provenance"
        raise RuntimeError(message)
    metadata = {
        "mode": args.mode, "samples": args.samples, "python": sys.version,
        "head": subprocess.check_output([git, "-C", str(_ROOT), "rev-parse", "HEAD"], text=True).strip(),  # noqa: S603 -- resolved executable and fixed Git arguments
        "source_hashes": before,
    }
    with MeTTa(metta_path=str(_ROOT)) as bootstrap:
        if args.mode in {"folding-control", "combined-control"}:
            bootstrap.runtime.must(
                "abolish(translator:fold_native_scalar_call/5), "
                "assertz((translator:fold_native_scalar_call(_, _, _, _, _) :- fail))"
            )
        if args.mode in {"metadata-control", "combined-control"}:
            _legacy_metadata_reads(bootstrap)
        metadata["swi"] = bootstrap.runtime.must("current_prolog_flag(version, Version)")["Version"]
    sequence = 0
    for sample in range(1, args.samples + 1):
        for kind, sizes in (
            ("fixed-list-maximum", [256, 1024, 4096, 16384]),
            ("nested-additions", [128, 512, 2048, 8192]),
        ):
            for size in sizes:
                if kind == "fixed-list-maximum":
                    expression = "(max-atom (" + "0 " * (size - 1) + "1))"
                    expected = 1
                else:
                    expression = "(+ 1 " * size + "1" + ")" * size
                    expected = size + 1
                for queries in sorted({16, 256, size}):
                    sequence += 1
                    name = f"folding-phase-{sequence:05}"
                    source = f"(= ({name}) {expression})"
                    query = f"!({name})"
                    with MeTTa(metta_path=str(_ROOT)) as m:
                        result, registration = _measure(m, m.run, source)
                        assert result == []
                        after_registration = _inspect_definition(m, name)
                        assert after_registration["Compiled"] in (False, "false")
                        result, first = _measure(m, m.run, query)
                        assert result == [[expected]]
                        _, repeated = _measure(m, _run_queries, m, query, expected, queries)
                        after_queries = _inspect_definition(m, name)
                        assert after_queries["Compiled"] in (True, "true")
                        assert after_queries["Materialized"] in (False, "false")
                    preparation = {meter: registration[meter] + first[meter] for meter in first}
                    total = {meter: preparation[meter] + repeated[meter] for meter in first}
                    print(json.dumps({
                        "mode": args.mode, "sample": sample, "kind": kind,
                        "size": size, "queries": queries, "completed_answers": queries + 1,
                        "source_chars": len(source), "query_chars": len(query), "answer": expected,
                        "inference_scope": "SWI only; excludes Python and native-call internals",
                        "after_registration": after_registration, "after_queries": after_queries,
                        "registration": registration, "first_query": first,
                        "preparation": preparation, "repeated": repeated, "total": total,
                    }), flush=True)
    metadata["rows"] = sequence
    finish_metadata(args.metadata, metadata, before)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
