"""Purpose: measure PeTTa memory use and scaling in fresh worker processes.

Assumes:
  - Linux exposes /proc/self/status, /proc/self/smaps_rollup, and
    /proc/self/clear_refs.
  - SWI statistics/2 and predicate_property/2 report exact structural
    counters for the process embedded by petta.
Guarantees:
  - every sample is returned with its raw counter values; aggregation keeps
    all repetitions, selects the minimum as the representative value, and
    reports the complete observed noise band.
  - fixed-width generated symbols do not add an accidental N log N text-size
    term to atom-memory curves.
  - page-based process memory is reported but never gates the initial
    baseline; only deterministic SWI bytes/counts and inference shapes do.
Owns resources:
  - every workload drops or empties the spaces and temporary files it creates;
    the parent process joins, terminates, or kills every worker through the
    lifecycle callback supplied by bench.py.
Decides:
  - geometric sizes 10 through 10,000 are the standard curve, three fresh
    repetitions are the minimum, and candidate fits are constant, logarithmic,
    linear, N log N, and quadratic.

[source: SWI-Prolog predicate and clause size accounting,
https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-proc.c#L3676-L3678;
commit=WORKTREE]
[source: Linux proc high-water reset and resident fields,
https://github.com/torvalds/linux/blob/028ef9c96e96197026887c0f092424679298aae8/Documentation/filesystems/proc.rst#L221-L224;
commit=WORKTREE]
[source: Google Benchmark complexity fitting with geometric ranges and
normalized RMS,
https://github.com/google/benchmark/blob/eddb0241389718a23a42db6af5f0164b6e0139af/docs/user_guide.md#L496-L524;
commit=WORKTREE]
"""

from __future__ import annotations

import gc
import json
import math
import os
import resource
import tempfile
import tracemalloc
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Literal

from petta import MeTTa, S, V

STANDARD_SIZES = (10, 100, 1_000, 10_000)
WIDE_SIZES = (1, 10, 100, 1_000)
MORK_WIDTH_SIZES = (1, 10, 100, 1_000)
DEFAULT_REPETITIONS = 3
SCHEMA_VERSION = 1

_MODEL_ORDER = {
    "constant": 0,
    "log_n": 1,
    "linear": 2,
    "n_log_n": 3,
    "quadratic": 4,
}
_PROCESS_METRICS = frozenset(
    {
        "private_steady_bytes",
        "pss_steady_bytes",
        "rss_lifetime_peak_bytes",
        "rss_peak_bytes",
        "rss_steady_bytes",
        "vm_size_steady_bytes",
    }
)


@dataclass(frozen=True)
class CurveCase:
    """One workload family and the metric that expresses its intended shape."""

    name: str
    sizes: tuple[int, ...]
    expected: str
    primary_metric: str
    workload: str
    gate: bool = True


CASES: dict[str, CurveCase] = {
    "atom-reclamation": CurveCase(
        "atom-reclamation", STANDARD_SIZES, "constant", "post_gc_atom_count",
        "atom_reclamation",
    ),
    "stored-atoms-native": CurveCase(
        "stored-atoms-native", STANDARD_SIZES, "linear", "storage_module_bytes",
        "stored_native",
    ),
    "stored-atoms-mork": CurveCase(
        "stored-atoms-mork", STANDARD_SIZES, "linear", "private_steady_bytes",
        "stored_mork", gate=False,
    ),
    "query-eager": CurveCase(
        "query-eager", STANDARD_SIZES, "linear", "python_peak_bytes", "query_eager",
        gate=False,
    ),
    "query-stream": CurveCase(
        "query-stream", STANDARD_SIZES, "linear", "inferences", "query_stream",
    ),
    "join-shared": CurveCase(
        "join-shared", WIDE_SIZES, "linear", "inferences", "join_shared",
    ),
    "join-projection": CurveCase(
        "join-projection", WIDE_SIZES, "linear", "inferences", "join_projection",
    ),
    "compiled-equations": CurveCase(
        "compiled-equations", STANDARD_SIZES, "linear", "compiled_predicate_bytes",
        "compiled_equations",
    ),
    "live-spaces": CurveCase(
        "live-spaces", WIDE_SIZES, "linear", "live_module_bytes", "live_spaces",
    ),
    "support-drop-spaces": CurveCase(
        "support-drop-spaces", WIDE_SIZES, "linear", "inferences",
        "support_drop_spaces",
    ),
    "support-drop-one": CurveCase(
        "support-drop-one", WIDE_SIZES, "linear", "inferences", "support_drop_one",
    ),
    "hyperpose-branches": CurveCase(
        "hyperpose-branches", WIDE_SIZES, "linear", "inferences", "hyperpose",
    ),
    "save-metta": CurveCase(
        "save-metta", STANDARD_SIZES, "linear", "inferences", "save_metta",
    ),
    "load-metta": CurveCase(
        "load-metta", STANDARD_SIZES, "linear", "inferences", "load_metta",
    ),
    "save-fast": CurveCase(
        "save-fast", STANDARD_SIZES, "linear", "inferences", "save_fast",
    ),
    "load-fast": CurveCase(
        "load-fast", STANDARD_SIZES, "linear", "inferences", "load_fast",
    ),
    "mork-join-width": CurveCase(
        "mork-join-width", MORK_WIDTH_SIZES, "linear", "inferences",
        "mork_join_width",
    ),
    "space-reuse": CurveCase(
        "space-reuse", WIDE_SIZES, "constant", "second_cycle_module_delta",
        "space_reuse",
    ),
    "table-reclamation": CurveCase(
        "table-reclamation", STANDARD_SIZES, "constant", "table_bytes_after_clear",
        "table_reclamation",
    ),
    "wire-intern-symbols": CurveCase(
        "wire-intern-symbols", (100, 1_000, 10_000, 100_000), "linear",
        "wire_cache_entries", "wire_intern",
    ),
}


def _fixed_symbol(prefix: str, index: int) -> Any:
    return S[f"{prefix}{index:08x}"]


def _proc_kib(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        name, raw = line.split(":", 1)
        fields = raw.split()
        if fields and fields[0].isdigit():
            multiplier = 1_024 if len(fields) > 1 and fields[1] == "kB" else 1
            values[name] = int(fields[0]) * multiplier
    return values


def _process_snapshot() -> dict[str, int]:
    status = _proc_kib(Path("/proc/self/status"))
    rollup = _proc_kib(Path("/proc/self/smaps_rollup"))
    return {
        "rss": status["VmRSS"],
        "rss_peak": status["VmHWM"],
        "vm_size": status["VmSize"],
        "pss": rollup["Pss"],
        "private": rollup.get("Private_Clean", 0) + rollup.get("Private_Dirty", 0),
    }


def _reset_rss_high_water() -> None:
    Path("/proc/self/clear_refs").write_text("5\n", encoding="ascii")


def _swi_snapshot(space: MeTTa) -> dict[str, int]:
    row = space.runtime.once(
        "statistics(atoms, AtomCount), statistics(atom_space, AtomSpace),"
        " statistics(globalused, GlobalUsed), statistics(localused, LocalUsed),"
        " statistics(trailused, TrailUsed), statistics(stack, Stack),"
        " statistics(table_space_used, TableSpace), statistics(modules, Modules),"
        " statistics(agc, Agc), statistics(agc_gained, AgcGained),"
        " statistics(cgc, Cgc), statistics(cgc_gained, CgcGained)"
    )
    return {
        "atom_count": int(row["AtomCount"]),
        "atom_space_bytes": int(row["AtomSpace"]),
        "global_used_bytes": int(row["GlobalUsed"]),
        "local_used_bytes": int(row["LocalUsed"]),
        "trail_used_bytes": int(row["TrailUsed"]),
        "stack_bytes": int(row["Stack"]),
        "table_space_bytes": int(row["TableSpace"]),
        "module_count": int(row["Modules"]),
        "agc_count": int(row["Agc"]),
        "agc_gained": int(row["AgcGained"]),
        "cgc_count": int(row["Cgc"]),
        "cgc_gained": int(row["CgcGained"]),
    }


def _space_module_snapshot(space: MeTTa) -> dict[str, int]:
    row = space.runtime.once(
        "( native_storage_module_ready(Space, _Storage)"
        " -> module_property(_Storage, size(StorageBytes)),"
        "    module_property(_Storage, program_size(StorageProgram))"
        " ;  StorageBytes = 0, StorageProgram = 0 ),"
        "space_module(Space, _Execution),"
        "module_property(_Execution, size(ExecutionBytes)),"
        "module_property(_Execution, program_size(ExecutionProgram))",
        Space=space.space_name,
    )
    return {
        "storage_module_bytes": int(row["StorageBytes"]),
        "storage_program_bytes": int(row["StorageProgram"]),
        "execution_module_bytes": int(row["ExecutionBytes"]),
        "execution_program_bytes": int(row["ExecutionProgram"]),
    }


def _snapshot(space: MeTTa) -> dict[str, int]:
    return _swi_snapshot(space) | _space_module_snapshot(space) | _process_snapshot()


def _difference(after: Mapping[str, int], before: Mapping[str, int]) -> dict[str, int]:
    return {name: int(after[name] - before[name]) for name in after.keys() & before.keys()}


def _measure(
    space: MeTTa,
    operation: Callable[[], Any],
    *,
    extras: Callable[[Any], Mapping[str, int]] | None = None,
) -> dict[str, int]:
    tracemalloc.start(1)
    gc.collect()
    python_before, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    before = _snapshot(space)
    _reset_rss_high_water()
    with space.stats() as stats:
        outcome = operation()
    after = _snapshot(space)
    python_after, python_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    deltas = _difference(after, before)
    metrics = {
        "inferences": int(stats.inferences),
        "python_steady_bytes": int(python_after - python_before),
        "python_peak_bytes": int(python_peak - python_before),
        "rss_steady_bytes": deltas.pop("rss"),
        "rss_peak_bytes": max(0, int(after["rss_peak"] - before["rss"])),
        "vm_size_steady_bytes": deltas.pop("vm_size"),
        "pss_steady_bytes": deltas.pop("pss"),
        "private_steady_bytes": deltas.pop("private"),
        "rss_lifetime_peak_bytes": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1_024
        ),
    }
    deltas.pop("rss_peak", None)
    metrics.update(deltas)
    if extras is not None:
        metrics.update({name: int(value) for name, value in extras(outcome).items()})
    return metrics


def _drop_all(spaces: Sequence[MeTTa]) -> None:
    for space in spaces:
        space.drop()


def _stored_native(size: int) -> dict[str, int]:
    space = MeTTa().new_space()
    atoms = [S.memscale_atom(_fixed_symbol("msn", index)) for index in range(size)]
    try:
        return _measure(space, lambda: space.add(*atoms))
    finally:
        space.drop()


def _stored_mork(size: int) -> dict[str, int]:
    space = MeTTa().space("&mork:memscale-storage")
    atoms = [S.memscale_atom(_fixed_symbol("msm", index)) for index in range(size)]
    try:
        return _measure(space, lambda: space.add(*atoms))
    finally:
        for atom in space.atoms():
            space.remove(atom)


def _query_answers(size: int, *, stream: bool) -> dict[str, int]:
    space = MeTTa().new_space()
    space.add(*(S.memscale_row(_fixed_symbol("msq", index)) for index in range(size)))

    def operation() -> int:
        if not stream:
            return len(space.query(S.memscale_row(V.value)))
        with space.stream(S.memscale_row(V.value)) as rows:
            return sum(1 for _ in rows)

    try:
        return _measure(space, operation, extras=lambda count: {"answer_count": count})
    finally:
        space.drop()


def _join_width(size: int, *, projection: bool, mork: bool = False) -> dict[str, int]:
    root = MeTTa()
    space = root.space("&mork:memscale-join") if mork else root.new_space()
    facts = []
    patterns = []
    for index in range(size):
        relation = _fixed_symbol("msj", index)
        facts.append(relation(S.only))
        variable = V[f"column_{index:08x}"] if projection else V.shared
        patterns.append(relation(variable))
    space.add(*facts)
    try:
        return _measure(
            space,
            lambda: space.query(*patterns),
            extras=lambda rows: {
                "answer_count": len(rows),
                "column_count": len(rows.columns),
            },
        )
    finally:
        if mork:
            for atom in space.atoms():
                space.remove(atom)
        else:
            space.drop()


def _compiled_predicate_bytes(space: MeTTa) -> dict[str, int]:
    row = space.runtime.once(
        "space_module(Space, _Module), functor(_Head, 'memscale-eq', 2),"
        " predicate_property(_Module:_Head, size(PredicateBytes)),"
        " findall(_ClauseBytes,"
        "   (clause(_Module:_Head, _Body, _Ref),"
        "    clause_property(_Ref, size(_ClauseBytes))), _ClauseSizes),"
        " sum_list(_ClauseSizes, ClauseBytes),"
        " ( predicate_property(_Module:_Head, indexed(_Indexes))"
        " -> findall(_IndexBytes,"
        "      (member(_Index, _Indexes), get_dict(size, _Index, _IndexBytes)),"
        "      _IndexSizes), sum_list(_IndexSizes, IndexBytes)"
        " ;  IndexBytes = 0 )",
        Space=space.space_name,
    )
    return {
        "compiled_predicate_bytes": int(row["PredicateBytes"]),
        "compiled_clause_bytes": int(row["ClauseBytes"]),
        "compiled_index_bytes": int(row["IndexBytes"]),
    }


def _compiled_equations(size: int) -> dict[str, int]:
    space = MeTTa().new_space()
    equations = [space.parse(f"(= (memscale-eq {index}) {index})") for index in range(size)]

    def operation() -> Any:
        space.add(*equations)
        return space.eval(S["memscale-eq"](size - 1))

    try:
        return _measure(space, operation, extras=lambda _result: _compiled_predicate_bytes(space))
    finally:
        space.drop()


def _sum_live_module_bytes(spaces: Sequence[MeTTa]) -> int:
    total = 0
    for space in spaces:
        total += _space_module_snapshot(space)["storage_module_bytes"]
        total += _space_module_snapshot(space)["execution_module_bytes"]
    return total


def _live_spaces(size: int) -> dict[str, int]:
    root = MeTTa()
    spaces: list[MeTTa] = []

    def operation() -> int:
        for _ in range(size):
            space = root.new_space()
            space.add(S.memscale_live(S.one))
            spaces.append(space)
        return len(spaces)

    try:
        return _measure(
            root,
            operation,
            extras=lambda _count: {"live_module_bytes": _sum_live_module_bytes(spaces)},
        )
    finally:
        _drop_all(spaces)


def _support_edge_count(root: MeTTa) -> int:
    return int(root.runtime.once("aggregate_all(count, support_graph:supports(_, _), N)")["N"])


def _support_drop_spaces(size: int) -> dict[str, int]:
    root = MeTTa()
    spaces: list[MeTTa] = []
    for index in range(size):
        space = root.new_space()
        space.run(f"(= (ms-support-{index:08x} $x) (+ $x 1))")
        spaces.append(space)
    edges = _support_edge_count(root)

    def operation() -> int:
        _drop_all(spaces)
        return edges

    return _measure(root, operation, extras=lambda count: {"support_edges": count})


def _support_drop_one(size: int) -> dict[str, int]:
    root = MeTTa()
    space = root.new_space()
    source = "\n".join(
        f"(= (ms-support-{index:08x} $x) (+ $x 1))" for index in range(size)
    )
    space.run(source)
    edges = _support_edge_count(root)
    return _measure(
        root,
        space.drop,
        extras=lambda _result: {"support_edges": edges},
    )


def _hyperpose(size: int) -> dict[str, int]:
    space = MeTTa().new_space()
    space.run("(= (memscale-branch $x) $x)")
    targets = [S["memscale-branch"](index) for index in range(size)]
    try:
        return _measure(
            space,
            lambda: space.hyperpose(*targets, timeout=120),
            extras=lambda answers: {"answer_count": len(answers)},
        )
    finally:
        space.drop()


def _atom_reclamation(size: int) -> dict[str, int]:
    root = MeTTa()

    def operation() -> dict[str, int]:
        root.runtime.must("garbage_collect")
        root.runtime.must("garbage_collect_clauses")
        root.runtime.must("garbage_collect_atoms")
        before = _swi_snapshot(root)
        space = root.new_space()
        atoms = [S.memscale_gc(_fixed_symbol("msg", index)) for index in range(size)]
        space.add(*atoms)
        loaded = _swi_snapshot(root)
        space.drop()
        del atoms
        gc.collect()
        root.runtime.must("garbage_collect")
        root.runtime.must("garbage_collect_clauses")
        root.runtime.must("garbage_collect_atoms")
        after = _swi_snapshot(root)
        return {
            "loaded_atom_count": loaded["atom_count"] - before["atom_count"],
            "loaded_atom_space_bytes": loaded["atom_space_bytes"] - before["atom_space_bytes"],
            "post_gc_atom_count": after["atom_count"] - before["atom_count"],
            "post_gc_atom_space_bytes": after["atom_space_bytes"] - before["atom_space_bytes"],
            "agc_cycles": after["agc_count"] - before["agc_count"],
            "agc_gained": after["agc_gained"] - before["agc_gained"],
            "cgc_cycles": after["cgc_count"] - before["cgc_count"],
            "cgc_gained": after["cgc_gained"] - before["cgc_gained"],
        }

    return _measure(root, operation, extras=lambda result: result)


def _execution_owned_count(root: MeTTa, name: str) -> int:
    row = root.runtime.once(
        "atom_string(_Space, SpaceText), space_module(_Space, _Module),"
        " aggregate_all(count,"
        "   (current_predicate(_Module:_Name/_Arity),"
        "    functor(_Head, _Name, _Arity),"
        "    \\+ predicate_property(_Module:_Head, imported_from(_))), Count)",
        SpaceText=name,
    )
    return int(row["Count"])


def _space_reuse(size: int) -> dict[str, int]:
    root = MeTTa()

    def cycle() -> tuple[list[str], int]:
        spaces = [root.new_space() for _ in range(size)]
        names = [str(space.space_name) for space in spaces]
        for index, space in enumerate(spaces):
            space.run(
                f"(= (ms-life-{index:08x} $x) (+ $x 1))\n"
                f"!((|-> ($x) (* $x 2)) {index})"
            )
        module_count = _swi_snapshot(root)["module_count"]
        _drop_all(spaces)
        return names, module_count

    def operation() -> dict[str, int]:
        before_modules = _swi_snapshot(root)["module_count"]
        first_names, first_modules = cycle()
        first_owned = sum(_execution_owned_count(root, name) for name in first_names)
        second_names, second_modules = cycle()
        second_owned = sum(_execution_owned_count(root, name) for name in second_names)
        return {
            "first_cycle_module_delta": first_modules - before_modules,
            "second_cycle_module_delta": second_modules - first_modules,
            "first_cycle_owned_after_drop": first_owned,
            "second_cycle_owned_after_drop": second_owned,
            "reused_name_count": len(set(first_names) & set(second_names)),
        }

    return _measure(root, operation, extras=lambda result: result)


def _table_bytes(space: MeTTa) -> dict[str, int]:
    row = space.runtime.once(
        "space_module(Space, _Module), functor(_Head, 'ms-table', 2),"
        " findall(_Bytes, table_statistics(_Module:_Head, space, _Bytes), _Sizes),"
        " sum_list(_Sizes, Total), statistics(table_space_used, Private)",
        Space=space.space_name,
    )
    return {"total": int(row["Total"]), "private": int(row["Private"])}


def _table_reclamation(size: int) -> dict[str, int]:
    space = MeTTa().new_space()
    space.run("!(import! (context-space) (library lib_tabling))")
    space.add(*(S["ms-table-row"](index) for index in range(size)))
    space.run(
        f"(= (ms-table $x) (match {space.space_name} (ms-table-row $x) $x))"
    )

    def operation() -> dict[str, int]:
        space.run("!(tabled (ms-table $x))")
        answers = space.run("!(collapse (ms-table $x))")
        populated = _table_bytes(space)
        space.add(S["ms-table-row"](size))
        invalidated = _table_bytes(space)
        space.run("!(table-clear (ms-table $x))")
        cleared = _table_bytes(space)
        return {
            "table_answer_count": len(answers[0][0].children),
            "table_bytes_populated": populated["total"],
            "table_bytes_invalidated": invalidated["total"],
            "table_bytes_after_clear": cleared["total"],
            "private_table_bytes_populated": populated["private"],
            "private_table_bytes_invalidated": invalidated["private"],
            "private_table_bytes_after_clear": cleared["private"],
        }

    try:
        return _measure(space, operation, extras=lambda result: result)
    finally:
        space.drop()


def _wire_intern(size: int) -> dict[str, int]:
    from petta._atoms_core import (  # noqa: PLC0415  -- the instrument measures this owned cache
        _WIRE_CACHE_MAX,
        _WIRE_SYMS,
        _wire_intern_clear,
    )

    _wire_intern_clear()
    space = MeTTa().new_space()
    space.add(*(S.memscale_wire(_fixed_symbol("msw", index)) for index in range(size)))

    def operation() -> Any:
        return space.query(S.memscale_wire(V.value))

    try:
        return _measure(
            space,
            operation,
            extras=lambda rows: {
                "answer_count": len(rows),
                "wire_cache_entries": len(_WIRE_SYMS),
                "wire_cache_limit": _WIRE_CACHE_MAX,
            },
        )
    finally:
        space.drop()
        _wire_intern_clear()


def _save_or_load(
    size: int,
    *,
    format_name: Literal["metta", "fast"],
    load: bool,
) -> dict[str, int]:
    directory = tempfile.TemporaryDirectory(prefix="petta-memory-scale-")
    suffix = ".metta" if format_name == "metta" else ".pfc"
    path = Path(directory.name) / f"space{suffix}"
    source = MeTTa().new_space()
    source.add(*(S.memscale_saved(index, index + 1) for index in range(size)))
    target: MeTTa | None = None
    if load:
        source.save(path, format=format_name)
        target = MeTTa().new_space()
        measured = target

        def operation() -> Any:
            return target.load(path)
    else:
        measured = source

        def operation() -> Any:
            return source.save(path, format=format_name)
    try:
        return _measure(
            measured,
            operation,
            extras=lambda result: {
                "file_bytes": path.stat().st_size,
                "stored_count": target.count() if target is not None else int(result),
            },
        )
    finally:
        source.drop()
        if target is not None:
            target.drop()
        directory.cleanup()


_WORKLOADS: dict[str, Callable[[int], dict[str, int]]] = {
    "atom_reclamation": _atom_reclamation,
    "stored_native": _stored_native,
    "stored_mork": _stored_mork,
    "query_eager": lambda size: _query_answers(size, stream=False),
    "query_stream": lambda size: _query_answers(size, stream=True),
    "join_shared": lambda size: _join_width(size, projection=False),
    "join_projection": lambda size: _join_width(size, projection=True),
    "compiled_equations": _compiled_equations,
    "live_spaces": _live_spaces,
    "support_drop_spaces": _support_drop_spaces,
    "support_drop_one": _support_drop_one,
    "hyperpose": _hyperpose,
    "save_metta": lambda size: _save_or_load(size, format_name="metta", load=False),
    "load_metta": lambda size: _save_or_load(size, format_name="metta", load=True),
    "save_fast": lambda size: _save_or_load(size, format_name="fast", load=False),
    "load_fast": lambda size: _save_or_load(size, format_name="fast", load=True),
    "mork_join_width": lambda size: _join_width(size, projection=False, mork=True),
    "space_reuse": _space_reuse,
    "table_reclamation": _table_reclamation,
    "wire_intern": _wire_intern,
}


def sample_worker(case_name: str, size: int, connection: Any) -> None:
    """Run one sample and send it to the parent before this process exits."""
    try:
        case = CASES[case_name]
        result = _WORKLOADS[case.workload](size)
        result["_worker_pid"] = os.getpid()
        connection.send({"ok": True, "metrics": result})
    except BaseException as exc:  # noqa: BLE001  -- worker failures cross the process boundary as evidence
        connection.send(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    finally:
        connection.close()


def _transform(model: str, size: int) -> float:
    if model == "constant":
        return 0.0
    if model == "log_n":
        return math.log(float(size))
    if model == "linear":
        return float(size)
    if model == "n_log_n":
        return float(size) * math.log(float(size))
    if model == "quadratic":
        return float(size * size)
    raise KeyError(model)


def _linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, float]:
    mean_x = fmean(xs)
    mean_y = fmean(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    slope = 0.0 if denominator == 0 else sum(
        (x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)
    ) / denominator
    intercept = mean_y - slope * mean_x
    residual = math.sqrt(
        fmean((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    )
    scale = max(max(ys) - min(ys), abs(mean_y), 1.0)
    return intercept, slope, residual / scale


def fit_curve(sizes: Sequence[int], values: Sequence[int | float]) -> dict[str, Any]:
    """Fit established complexity families and a descriptive log-log exponent."""
    if len(sizes) != len(values) or len(sizes) < 2:
        msg = "a curve fit needs equally sized sequences with at least two points"
        raise ValueError(msg)
    ys = [float(value) for value in values]
    models: dict[str, dict[str, float]] = {}
    for model in _MODEL_ORDER:
        intercept, slope, nrms = _linear_fit([_transform(model, n) for n in sizes], ys)
        models[model] = {"intercept": intercept, "slope": slope, "nrms": nrms}
    best = min(models, key=lambda name: (models[name]["nrms"], _MODEL_ORDER[name]))

    positive = [(float(n), float(y)) for n, y in zip(sizes, ys, strict=True) if y > 0]
    exponent: float | None = None
    if len(positive) >= 2:
        log_x = [math.log(n) for n, _ in positive]
        log_y = [math.log(y) for _, y in positive]
        _, exponent, _ = _linear_fit(log_x, log_y)
    return {
        "best_model": best,
        "models": models,
        "power_exponent": exponent,
        "last_ratio": None if values[-2] == 0 else float(values[-1]) / float(values[-2]),
    }


def aggregate_samples(
    case: CurveCase,
    raw: Mapping[int, Sequence[Mapping[str, int]]],
) -> dict[str, Any]:
    """Preserve samples, derive minima/noise, and fit every common metric."""
    sizes = sorted(raw)
    metric_names = set.intersection(
        *(set(sample) for samples in raw.values() for sample in samples)
    )
    metric_names = {name for name in metric_names if not name.startswith("_")}
    metrics: dict[str, Any] = {}
    for name in sorted(metric_names):
        samples_by_size = {
            str(size): [int(sample[name]) for sample in raw[size]] for size in sizes
        }
        representative = [min(samples_by_size[str(size)]) for size in sizes]
        spans = [
            max(samples_by_size[str(size)]) - min(samples_by_size[str(size)])
            for size in sizes
        ]
        relative = [
            span / max(abs(min(samples_by_size[str(size)])), 1)
            for size, span in zip(sizes, spans, strict=True)
        ]
        metrics[name] = {
            "samples": samples_by_size,
            "representative": representative,
            "noise": {
                "absolute_max": max(spans),
                "relative_max": max(relative),
                "resolution_bytes": 4_096 if name in _PROCESS_METRICS else 1,
            },
            "fit": fit_curve(sizes, representative),
            "gated": bool(case.gate and name == case.primary_metric and name not in _PROCESS_METRICS),
        }
    primary = metrics[case.primary_metric]
    expected_nrms = primary["fit"]["models"][case.expected]["nrms"]
    matches = (
        _MODEL_ORDER[primary["fit"]["best_model"]] <= _MODEL_ORDER[case.expected]
        or expected_nrms <= 0.10
    )
    return {
        "expected": case.expected,
        "primary_metric": case.primary_metric,
        "sizes": sizes,
        "matches_expectation": matches,
        "worker_pids": {
            str(size): [int(sample["_worker_pid"]) for sample in raw[size]]
            for size in sizes
        },
        "metrics": metrics,
    }


def _atomic_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def baseline_document(results: Mapping[str, Any], *, cause_commit: str) -> dict[str, Any]:
    """Reduce a complete run to pinned curves while retaining every noise band."""
    cases: dict[str, Any] = {}
    for name, result in results["cases"].items():
        primary = result["metrics"][result["primary_metric"]]
        cases[name] = {
            "expected": result["expected"],
            "primary_metric": result["primary_metric"],
            "sizes": result["sizes"],
            "representative": primary["representative"],
            "noise": primary["noise"],
            "fit": primary["fit"],
            "gated": primary["gated"],
            "cause": {
                "commit": cause_commit,
                "chain": [
                    f"bench.py --memory-scale spawns {name} in a fresh process",
                    f"{result['primary_metric']} is selected by minimum of repetitions",
                    f"the intended complexity family is {result['expected']}",
                ],
            },
        }
    return {
        "schema": SCHEMA_VERSION,
        "repetitions": results["repetitions"],
        "cases": cases,
        "repin_rule": (
            "A changed pin must name the first causal code or dependency change, "
            "carry the old and new raw samples and noise bands, and explain why the "
            "new curve still matches its declared complexity. Never re-pin to hide "
            "an unexplained move."
        ),
    }


def compare_baseline(results: Mapping[str, Any], baseline: Mapping[str, Any]) -> list[str]:
    """Return every deterministic pin or growth-shape regression."""
    failures: list[str] = []
    if baseline.get("schema") != SCHEMA_VERSION:
        return [f"memory-scale baseline schema is {baseline.get('schema')}, expected {SCHEMA_VERSION}"]
    for name, pin in baseline["cases"].items():
        if name not in results["cases"]:
            failures.append(f"missing pinned case {name}")
            continue
        result = results["cases"][name]
        metric = result["metrics"][pin["primary_metric"]]
        if result["sizes"] != pin["sizes"]:
            failures.append(f"{name}: sizes changed from {pin['sizes']} to {result['sizes']}")
            continue
        if not pin["gated"]:
            continue
        pinned = int(pin["representative"][-1])
        current = int(metric["representative"][-1])
        band = max(int(pin["noise"]["absolute_max"]) * 2, 4)
        allowance = max(band, math.ceil(abs(pinned) * 0.05))
        if current > pinned + allowance:
            failures.append(
                f"{name}: {pin['primary_metric']} moved {pinned} -> {current}; "
                f"allowance is {allowance} from the pinned noise band and 5% margin"
            )
        expected_nrms = metric["fit"]["models"][pin["expected"]]["nrms"]
        if expected_nrms > 0.10 and _MODEL_ORDER[metric["fit"]["best_model"]] > _MODEL_ORDER[pin["expected"]]:
            failures.append(
                f"{name}: fitted {metric['fit']['best_model']} instead of "
                f"{pin['expected']} (normalized RMS {expected_nrms:.4f})"
            )
    return failures


def run_suite(  # noqa: C901  -- the loop keeps each process, payload, and failure in one lifecycle
    *,
    names: Sequence[str],
    repetitions: int,
    timeout: float,
    quick: bool,
    output: Path | None,
    baseline_path: Path,
    update_baseline: bool,
    cause_commit: str,
    keep_going: bool,
    context: Any,
    finish_process: Callable[[Any, float], str | None],
) -> int:
    """Run selected curve families, aggregate them, and compare or update pins."""
    selected = list(names or sorted(CASES))
    raw_cases: dict[str, dict[int, list[Mapping[str, int]]]] = {}
    errors: list[str] = []
    for name in selected:
        case = CASES[name]
        sizes = case.sizes[:2] if quick else case.sizes
        case_raw: dict[int, list[Mapping[str, int]]] = {size: [] for size in sizes}
        for size in sizes:
            for repetition in range(repetitions):
                parent, child = context.Pipe(duplex=False)
                process = context.Process(
                    target=sample_worker,
                    args=(name, size, child),
                    name=f"petta-memory-{name}-{size}-{repetition}",
                )
                process.start()
                child.close()
                failure = finish_process(process, timeout)
                if failure is None and parent.poll():
                    message = parent.recv()
                    if message["ok"]:
                        case_raw[size].append(message["metrics"])
                    else:
                        failure = message["error"]
                elif failure is None:
                    failure = "worker exited without a measurement"
                parent.close()
                if failure is not None:
                    detail = f"{name}[{size}] repetition {repetition + 1}: {failure}"
                    errors.append(detail)
                    print(detail)
                    if not keep_going:
                        return 1
        if all(case_raw.values()):
            raw_cases[name] = case_raw

    document: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "repetitions": repetitions,
        "loadavg": Path("/proc/loadavg").read_text(encoding="ascii").strip(),
        "cases": {
            name: aggregate_samples(CASES[name], raw) for name, raw in raw_cases.items()
        },
        "errors": errors,
    }
    if output is not None:
        _atomic_json(output, document)
        print(f"wrote memory-scale data to {output}")

    for name, result in document["cases"].items():
        primary = result["metrics"][result["primary_metric"]]
        fit = primary["fit"]
        print(
            f"{name}: {result['primary_metric']} {primary['representative']}; "
            f"fit={fit['best_model']} expected={result['expected']} "
            f"nrms={fit['models'][result['expected']]['nrms']:.4f} "
            f"noise=+/-{primary['noise']['absolute_max']}"
        )

    if quick:
        return int(bool(errors))
    if update_baseline:
        _atomic_json(baseline_path, baseline_document(document, cause_commit=cause_commit))
        print(f"wrote memory-scale baseline to {baseline_path}")
        return int(bool(errors))
    if not baseline_path.exists():
        print(f"memory-scale baseline is absent: {baseline_path}")
        return int(bool(errors))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    failures = compare_baseline(document, baseline)
    for failure in failures:
        print(f"memory-scale regression: {failure}")
    return int(bool(errors or failures))
