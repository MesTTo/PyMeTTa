"""Purpose: reproduce native join and tagged-demand complexity curves.

Run each control in its own process from the repository root::

    PYTHONPATH=extensions/python $VENV/bin/python -m benchmarks.query_planning \
        join --metadata ai-tmp/join-planned.json
    PYTHONPATH=extensions/python $VENV/bin/python -m benchmarks.query_planning \
        demand --control --metadata ai-tmp/demand-reference.json

The empty two-hub triangle changes quadratic intermediate enumeration into
O(N log N) indexed intersection on this family. The three other join families
are the shapes it loses on, which is why planning is a declared pragma rather
than a default: the control arm is simply the engine's shipping behaviour. A
bound all-pairs tagged query changes cubic Python matching and quadratic
retained proofs into linear certification and indexing. Input storage is
prepared outside the measured query; each native query still constructs its
own Generic Join indexes.

Guarantees:
  - every measured query checks its exact result; demand checks value, tag,
    tokens and the sole proof before comparing complete rendered proof bags
    [tested: native_generic_join, test_demand_preserves_complete_derivation_bags;
    commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - mismatched source fingerprints before and after a run reject its result
    [source: source_snapshot and main in this file; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
Owns resources: each space and context closes after use. The native control
  is the shipping default, so it sets nothing; no source file changes.
  Metadata is written through atomic_json after all measurements finish.
Decides: five process-CPU samples are the default; samples and sizes must be
  positive. SWI inferences exclude Python and operations inside native calls.
  Demand matcher counts and unprofiled complete-call CPU expose that boundary.
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import random
import statistics
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from time import process_time_ns
from unittest.mock import patch

import metta.algebra as carrier
import metta.algebra._demand as demand
from benchmarks import atomic_json
from metta import MeTTa, S, V
from metta.algebra import AlgebraEvaluation, evaluate

_ROOT = Path(__file__).resolve().parents[3]


def source_snapshot() -> dict[str, str]:
    """Fingerprint sources used by the three query-planning sweep drivers."""
    paths = list(Path(__file__).resolve().parent.glob("query_planning*.py"))
    for folder, suffixes in (
        ("engine", {".pl", ".metta", ".c"}),
        ("lib", {".pl", ".metta"}),
        ("extensions/python/metta", {".py", ".pl"}),
    ):
        paths.extend(
            path for path in (_ROOT / folder).rglob("*")
            if path.is_file() and path.suffix in suffixes
        )
    return {
        path.relative_to(_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def finish_metadata(path: Path, metadata: dict[str, object], before: dict[str, str]) -> None:
    """Record source provenance and reject mismatched end-of-run fingerprints."""
    after = source_snapshot()
    metadata["source_unchanged"] = before == after
    metadata["changed_during_run"] = sorted(
        name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
    )
    atomic_json(path, metadata)
    assert before == after, metadata["changed_during_run"]


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        message = "sizes and samples must be positive integers"
        raise argparse.ArgumentTypeError(message)
    return number


def _cpu_samples(query: Callable[[], None], count: int) -> list[int]:
    samples = []
    for _ in range(count):
        started = process_time_ns()
        query()
        samples.append(process_time_ns() - started)
    return samples


_TRIANGLE = (
    "!(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) "
    "(triple $x $y $z))"
)
_JOIN_QUERIES = {
    "two-hub": _TRIANGLE,
    "uniform": _TRIANGLE,
    "clique": _TRIANGLE,
    "small-third": (
        "!(match &self (, (edge $x $y) (edge $y $z) (tag $z $x)) "
        "(triple $x $y $z))"
    ),
}
_JOIN_SIZES = {
    "two-hub": [64, 128, 256, 512, 1024, 2048, 4096, 8192],
    "uniform": [64, 128, 256, 512, 1024, 2048],
    "clique": [8, 16, 32, 48],
    "small-third": [64, 128, 256, 512, 1024, 2048],
}


def _two_hub_edges(edges: int) -> list[object]:
    return [
        S.edge(a, b)
        for leaf in range(1, edges // 4 + 1)
        for hub in (-1, -2)
        for a, b in ((leaf, hub), (hub, leaf))
    ]


def _join_atoms(family: str, size: int) -> list[object]:
    """Two-hub skew wins; uniform degree, a clique and a one-row third lose."""
    if family == "two-hub":
        return _two_hub_edges(size)
    if family == "small-third":
        return [*_two_hub_edges(size), S.tag(-1, -2)]
    if family == "clique":
        return [S.edge(a, b) for a in range(size) for b in range(size) if a != b]
    generator = random.Random(4242)
    return [
        S.edge(generator.randrange(size), generator.randrange(size))
        for _ in range(2 * size)
    ]


def _join_size(m: MeTTa, family: str, size: int, samples: int) -> dict[str, object]:
    with m.space() as space:
        space.add(*_join_atoms(family, size))
        query = _JOIN_QUERIES[family]
        expected = space.run(query)

        def checked_query() -> None:
            assert space.run(query) == expected

        checked_query()
        with m.stats() as spent:
            checked_query()
        cpu = _cpu_samples(checked_query, samples)
    return {
        "family": family, "edges": size, "inferences": spent.inferences,
        "answers": len(expected[0]) if expected else 0,
        "inference_scope": "SWI only; excludes Python and native sort/comparison internals",
        "cpu_ns": cpu, "cpu_median_ns": statistics.median(cpu),
        "cpu_min_ns": min(cpu), "cpu_max_ns": max(cpu),
    }


def _proof_bag(result: AlgebraEvaluation) -> list[tuple[object, ...]]:
    return [
        (str(answer.value), str(answer.tag), sorted(answer.tokens),
         answer.proof, answer.why().render())
        for answer in result.answers
    ]


def _demand_size(m: MeTTa, seeds: int, samples: int, *, control: bool) -> dict[str, object]:
    with m.space() as space:
        for value in range(seeds):
            space.add_tagged_fact(1, S.seed(value))
        space.add_tagged_rule(1, S.pair(V.x, V.y), S.seed(V.x), S.seed(V.y))
        goal = S.pair(0, 0)
        profile = cProfile.Profile()
        with m.stats() as spent:
            profile.enable()
            result = evaluate(space, goal, algebra="counting")
            profile.disable()
        assert len(result.answers) == 1
        answer = result.answers[0]
        assert str(answer.value) == "(pair 0 0)"
        assert str(answer.tag) == "1"
        assert answer.proof == (seeds, 0, 0)
        assert answer.tokens == frozenset({0})
        expected = _proof_bag(result)

        def checked_query() -> None:
            assert _proof_bag(evaluate(space, goal, algebra="counting")) == expected

        cpu = _cpu_samples(checked_query, samples)
        entries = profile.getstats()
        matches = sum(row.callcount for row in entries if row.code is carrier._match.__code__)
        shapes = sum(row.callcount for row in entries if row.code is demand._shape.__code__)
        assert matches == (seeds**3 + 4 * seeds**2 + 3 * seeds if control else 3)
        assert shapes == (0 if control else 2 * seeds + 10)
    return {
        "seeds": seeds, "match_calls": matches, "shape_calls": shapes,
        "profiler_total_calls": sum(row.callcount for row in entries),
        "inferences": spent.inferences, "answers": 1,
        "proof_bag": expected,
        "inference_scope": "SWI transport only; excludes the Python evaluator",
        "cpu_ns": cpu, "cpu_median_ns": statistics.median(cpu),
        "cpu_min_ns": min(cpu), "cpu_max_ns": max(cpu),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Write a size ladder with paired work meters and source provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workload", choices=("join", "demand"))
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--family", choices=tuple(_JOIN_SIZES), default="two-hub")
    parser.add_argument("--sizes", nargs="+", type=_positive)
    parser.add_argument("--samples", type=_positive, default=5)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    sizes = args.sizes or (
        _JOIN_SIZES[args.family]
        if args.workload == "join" else [16, 32, 64, 128, 256]
    )
    if (args.workload == "join" and args.family in {"two-hub", "small-third"}
            and any(size % 4 for size in sizes)):
        parser.error("two-hub edge counts must be multiples of four")
    before = source_snapshot()
    metadata = {
        "workload": args.workload, "control": args.control,
        "family": args.family if args.workload == "join" else None,
        "sizes": sizes, "samples": args.samples, "python": sys.version,
        "source_hashes": before,
    }
    with MeTTa() as m:
        metadata["swi"] = m.runtime.must("current_prolog_flag(version, Version)")["Version"]
        if args.workload == "join":
            if not args.control:
                # The control is the shipping default, so only the planned arm
                # declares anything, through the pragma a program would use.
                with m.space() as declaring:
                    declaring.run("!(pragma! plan-cyclic-joins True)")
            for size in sizes:
                print(json.dumps({"mode": "control" if args.control else "planned",
                                  **_join_size(m, args.family, size, args.samples)}),
                      flush=True)
        else:
            with m.space() as warm:
                warm.add_tagged_fact(1, S.seed(0))
                warm.add_tagged_rule(1, S.pair(V.x, V.y), S.seed(V.x), S.seed(V.y))
                evaluate(warm, S.pair(0, 0), algebra="counting")
            implementation = (lambda *_a, **_kw: None) if args.control else carrier._demand_evaluate
            with patch.object(carrier, "_demand_evaluate", implementation):
                for size in sizes:
                    print(json.dumps({"mode": "reference" if args.control else "demand",
                                      **_demand_size(m, size, args.samples,
                                                     control=args.control)}), flush=True)
    finish_metadata(args.metadata, metadata, before)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
