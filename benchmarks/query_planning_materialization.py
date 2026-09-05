"""Purpose: measure preparation and complete function-free query workloads.

Run each construction control in its own process from the repository root::

    PYTHONPATH=extensions/python $VENV/bin/python \
        -m benchmarks.query_planning_materialization materialized \
        --load-mode run --metadata ai-tmp/materialized-run.json
    PYTHONPATH=extensions/python $VENV/bin/python \
        -m benchmarks.query_planning_materialization original \
        --load-mode fast --metadata ai-tmp/original-fast.json

Assumes: the fixed two-rule chain has n edges and one answer per ground query.
  The original path takes O(q*n) query work. The admitted image takes
  O(n**2 log n) preparation, O(n**2) storage and expected O(q) warmed query work.
  Transactional replacement also validates O(n) source clauses on its first
  query. The workload pays preparation and q=n**2 complete queries together.
Guarantees:
  - every measured query checks its exact one-occurrence bag, and each image
    is inspected only after the cold query [source: _measure_size;
    commit=WORKTREE]
  - changed source fingerprints reject a measurement [source:
    benchmarks.query_planning.finish_metadata; commit=WORKTREE]
Owns resources: spaces, contexts and temporary source/cache files close after
  use. The original control disables construction in this process only.
Decides: report SWI inferences and CPU beside complete-process CPU. Inferences
  exclude Python work and operations inside native calls. SWI CPU measures its
  calling thread and completed joined children; process CPU includes all
  process threads and system time [source: CPython v3.14.0
  Doc/library/time.rst, process_time; SWI V10.1.13 man/builtin.doc,
  statistics/2; commit=WORKTREE].
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from time import process_time_ns

import janus_swi

from benchmarks.query_planning import finish_metadata, source_snapshot
from metta import MeTTa, S


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        message = "sizes must be positive integers"
        raise argparse.ArgumentTypeError(message)
    return number


def _measure_size(m: MeTTa, n: int, mode: str, load_mode: str) -> dict[str, object]:
    source = "\n".join(f"(edge n{i} n{i + 1})" for i in range(n))
    source += "\n(= (reach $x $y) (match &self (edge $x $y) True))\n"
    source += "(= (reach $x $y) (match &self (edge $x $z) (reach $z $y)))\n"
    query = S.reach(S.n0, S[f"n{n}"])
    q = n * n
    with (
        TemporaryDirectory(prefix="ai-materialization-", dir="ai-tmp") as folder,
        m.space() as space,
    ):
        path = Path(folder) / ("chain.fast" if load_mode == "fast" else "chain.metta")
        if load_mode != "run":
            if load_mode == "fast":
                with m.space() as saved:
                    saved.run(source)
                    saved.save(path, format="fast")
            else:
                path.write_text(source, encoding="utf-8")
            # The measured second load exercises the transactional
            # replacement boundary, including its first-query receipt.
            space.load(path)

        total_started = process_time_ns()
        with space.stats() as total:
            load_started = process_time_ns()
            with space.stats() as loading:
                if load_mode == "run":
                    space.run(source)
                else:
                    space.load(path)
            load_cpu = process_time_ns() - load_started

            queries_started = process_time_ns()
            with space.stats() as queries:
                first_started = process_time_ns()
                with space.stats() as first:
                    assert Counter(map(str, space.eval(query))) == {"True": 1}
                first_cpu = process_time_ns() - first_started
                for _ in range(q - 1):
                    assert Counter(map(str, space.eval(query))) == {"True": 1}
            queries_cpu = process_time_ns() - queries_started
        total_cpu = process_time_ns() - total_started

        warmed_started = process_time_ns()
        with space.stats() as warmed:
            assert Counter(map(str, space.eval(query))) == {"True": 1}
        warmed_cpu = process_time_ns() - warmed_started

        # The public API has no relation-size observer. Inspect the trie
        # after measurement so this probe cannot prepare a lazy index.
        stored = janus_swi.query_once(
            "materialize:materialized_snapshot(S,_M,_T,_Stamp,_Functions),"
            "trie_property(_T,value_count(Rows)),trie_property(_T,size(Bytes))",
            {"S": str(space.name)},
        )
        assert stored["truth"] == (mode == "materialized"), stored
        phases = {
            "load": (loading, load_cpu), "first": (first, first_cpu),
            "queries": (queries, queries_cpu), "total": (total, total_cpu),
            "warmed": (warmed, warmed_cpu),
        }
        return {
            "mode": mode, "load_mode": load_mode, "n": n, "q": q,
            "inference_scope": "SWI only; excludes Python and native-call internals",
            "checked_query_bags": q + 1,
            "stored_rows": stored.get("Rows", 0),
            "stored_bytes": stored.get("Bytes", 0),
            **{
                name: {
                    "inferences": spent.inferences,
                    "swi_cpu_seconds": spent.cputime,
                    "process_cpu_ns": cpu,
                }
                for name, (spent, cpu) in phases.items()
            },
        }


def main(argv: Sequence[str] | None = None) -> int:
    """Write JSON rows for load, first query, warm query and their paid total."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("materialized", "original"))
    parser.add_argument("--sizes", nargs="+", type=_positive,
                        default=[16, 32, 64, 128, 256, 512])
    parser.add_argument("--load-mode", choices=("run", "reload", "fast"), default="run")
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    before = source_snapshot()
    metadata = {
        "workload": "materialization", "mode": args.mode,
        "load_mode": args.load_mode, "sizes": args.sizes,
        "python": sys.version, "source_hashes": before,
        "inference_scope": "SWI only; excludes Python and native-call internals",
        "swi_cpu_scope": "SWI calling thread user CPU, including completed joined threads",
        "process_cpu_scope": "current process user and system CPU across all threads",
        "workload_scope": "one preparation plus q=n*n queries; first is included in q",
    }
    Path("ai-tmp").mkdir(exist_ok=True)
    with MeTTa() as m:
        metadata["swi"] = m.runtime.must("current_prolog_flag(version, Version)")["Version"]
        if args.mode == "original":
            m.runtime.must(
                "abolish(materialize:with_source_materialization/3),"
                "assertz((materialize:with_source_materialization(_Space,_Names,_Goal)"
                ":-call(_Goal))),"
                "abolish(materialize:flush_source_materialization/0),"
                "assertz(materialize:flush_source_materialization),"
                "abolish(materialize:materialize_source/1),"
                "assertz(materialize:materialize_source(_))"
            )
        for n in args.sizes:
            print(json.dumps(_measure_size(m, n, args.mode, args.load_mode)), flush=True)
    finish_metadata(args.metadata, metadata, before)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
