"""Purpose: pin interrupt and first-use dependency costs under concurrency.

Guarantees: 32 fresh engine processes compare corrected counters with polling
off and across several normal and dense heartbeat intervals
[tested: test_heartbeat_correction_is_exact_with_32_concurrent_workers; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
The first failed Janus query ignores deterministic file-cache expiry; a
skipped boot import exposes a 232-inference difference, including one extra
asserta/1 through assertion ownership during cache expiry [tested:
test_first_failed_text_query_has_no_deferred_dependency_cost;
commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
Decides: the three-twin measurement uses a 9223372036854775807-second
file-cache lifetime and warm compiled library artifacts to separate program
work from wall-clock cache sweeps and compilation-child launch costs
[tested: test_memo_and_tabling_first_use_costs_ignore_file_cache_expiry;
commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
Owns resources: every subprocess is joined; each worker drops its native space.
"""

from __future__ import annotations

import collections
import concurrent.futures
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def _prepare() -> None:
    sys.path.insert(0, str(ROOT / "extensions/python"))
    from _workspace import on_path

    on_path()


def _heartbeat_worker() -> dict:
    import janus_swi as janus

    from metta import Space

    rows = []
    with Space("&heartbeat-accounting") as space:
        janus.consult("heartbeat_accounting_work", data="""
            heartbeat_accounting_work(N) :- forall(between(1,N,_),true).
        """)
        for interval in (0, 100000, 1000, 0):
            janus.query_once("set_prolog_flag(heartbeat,Interval)", {"Interval": interval})
            for size, runs in ((200, 96), (200000, 16)):
                janus.cmd("user", "heartbeat_accounting_work", size)
                costs = collections.Counter()
                ticks = 0
                for _ in range(runs):
                    with space.stats() as spent:
                        janus.cmd("user", "heartbeat_accounting_work", size)
                    costs[spent.inferences] += 1
                    ticks += spent.heartbeats
                rows.append({"interval": interval, "size": size, "costs": dict(costs), "ticks": ticks})
    return {"rows": rows}


def _imports_worker() -> dict:
    import janus_swi as janus

    from metta import Space

    with Space("&binding-imports"):
        # current_predicate/1 does not resolve an unknown import. Test it
        # before asking which module supplies the already loaded predicate.
        return janus.query_once(
            "current_predicate(user:aggregate_all/3),"
            "predicate_property(user:aggregate_all(_,_,_),imported_from(aggregate)),"
            "current_predicate(user:gensym/2),"
            "predicate_property(user:gensym(_,_),imported_from(gensym)),"
            "current_predicate(user:limit/2),"
            "predicate_property(user:limit(_,_),imported_from(solution_sequences))"
        )


def _failure_worker(eager: bool, expiry: int) -> dict:  # noqa: FBT001 -- the worker protocol carries this import-presence bit as data
    import janus_swi as janus

    if not eager:
        # Plant the old boot behavior in this process only. Match the source
        # file as well as the directive so unrelated imports remain intact.
        shim = ROOT / "extensions/python/metta/_binding/shim.pl"
        janus.consult("binding_lazy_control", data=f"""
            :- multifile user:term_expansion/2.
            user:term_expansion((:- janus:use_module(library(apply), [maplist/2])), []) :-
                prolog_load_context(file, {str(shim)!r}).
        """)
    from metta import Space

    with Space("&first-failure") as space:
        assert janus.query_once("set_prolog_flag(heartbeat,0)")["truth"]
        assert janus.query_once("call(Goal)", {"Goal": "true"})["truth"]
        # Prime the actual dependency's alias outside the measured window.
        # Zero disables the cache and skips maintenance; -1 forces the
        # expired branch, including that maintenance. Neither control sleeps.
        prepared = janus.query_once(
            "absolute_file_name(library(apply),_,[file_type(prolog),access(read),"
            "file_errors(fail),relative_to(File)]),set_prolog_flag(file_search_cache_time,Expiry)",
            {"Expiry": expiry, "File": str(Path(janus.__file__).with_name("janus.pl"))},
        )
        assert prepared["truth"]
        try:
            with space.stats() as spent:
                result = janus.query_once("call(Goal)", {"Goal": "fail"})
        finally:
            assert janus.query_once("set_prolog_flag(file_search_cache_time,10)")["truth"]
        assert result["truth"] is False
        return {"eager": eager, "expiry": expiry, "cost": spent.inferences}


def _twin_worker(name: str, interval: int) -> dict:
    import janus_swi as janus

    # SWI engines inherit flags when created. Set the lane policy before boot
    # creates any engine, so held work shares the calling thread's lifetime.
    janus.cmd("system", "set_prolog_flag", "file_search_cache_time", 9223372036854775807)
    from metta import MeTTa

    path = (ROOT / "extensions/python/examples/language-feature-examples/ch18-performance"
            / "18-02-memoisation-and-tabling" / f"{name}.py")
    spec = importlib.util.spec_from_file_location("metta_counter_twin", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    space = MeTTa(metta_path=str(ROOT)).self
    try:
        janus.cmd("system", "set_prolog_flag", "heartbeat", interval)
        with space.stats() as spent:
            module.twin(space)
        return {"twin": name, "interval": interval, "cost": spent.inferences,
                "ticks": spent.heartbeats, "held": spent._engine_inferences,
                "collections": spent.gc_count}
    finally:
        assert janus.query_once("set_prolog_flag(file_search_cache_time,10)")["truth"]
        space.drop()


def _launch(arguments: tuple) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), json.dumps(arguments)],
                          cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False)


def _concurrent(arguments: list[tuple]) -> list[dict]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as workers:
        results = list(workers.map(_launch, arguments))
    assert all(result.returncode == 0 for result in results), [
        (result.returncode, result.stdout, result.stderr) for result in results if result.returncode
    ]
    return [json.loads(result.stdout) for result in results]


@pytest.fixture(scope="module")
def concurrent_workers():
    """Hold every polling interval in each of 32 fresh engine processes."""
    return _concurrent([("heartbeat",)] * 32)


def test_first_failed_text_query_has_no_deferred_dependency_cost():
    """Boot removes the expiry delta and the lazy-import plant restores it."""
    results = _concurrent([
        ("failure", eager, expiry)
        for _ in range(16) for eager in (False, True) for expiry in (10, 0, -1)
    ])
    costs = {}
    for result in results:
        costs.setdefault((result["eager"], result["expiry"]), set()).add(result["cost"])
    assert all(len(values) == 1 for values in costs.values()), costs
    one = {key: next(iter(values)) for key, values in costs.items()}
    assert one[True, -1] == one[True, 0] == one[True, 10], one
    # SWI's expired-cache branch refreshes the entry with asserta/1. The
    # assertion ownership wrapper adds three inferences to its former 229.
    # The eager path above must still have no expiry-dependent cost.
    assert one[False, -1] - one[False, 10] == 232, one
    assert one[False, 0] - one[False, 10] == 226, one


def test_binding_boot_resolves_its_direct_standard_library_dependencies():
    """Every direct standard-library call is imported before the first use."""
    assert _concurrent([("imports",)])[0]["truth"] is True


def test_memo_and_tabling_first_use_costs_ignore_file_cache_expiry():
    """The three complete twins keep one cost under the fixed cache policy."""
    names = ("08-memo_stats", "09-tabling_fib", "11-tabling_space_write")
    # Artifacts are shared by processes. Complete their first compilation
    # before sampling; each measured process still imports the library once.
    _concurrent([("twin", name, 0) for name in names])
    results = _concurrent([
        ("twin", name, interval)
        for _ in range(8) for name in names for interval in (0, 100000, 1000, 0)
    ])
    for name in names:
        samples = [result for result in results if result["twin"] == name]
        assert len({result["cost"] for result in samples}) == 1, samples


def test_heartbeat_correction_is_exact_with_32_concurrent_workers(concurrent_workers):
    """Every window has the disabled control's exact cost, regardless of ticks."""
    for result in concurrent_workers:
        rows = result["rows"]
        controls = {row["size"]: set(row["costs"]) for row in rows if row["interval"] == 0}
        assert all(len(costs) == 1 for costs in controls.values()), rows
        for row in rows:
            assert set(row["costs"]) == controls[row["size"]], rows
            if row["interval"] == 0:
                assert row["ticks"] == 0, row
            elif row["size"] == 200000:
                assert row["ticks"] >= 16 * 3, row


if __name__ == "__main__":
    _prepare()
    kind, *arguments = json.loads(sys.argv[1])
    workers = {"heartbeat": _heartbeat_worker, "failure": _failure_worker,
               "twin": _twin_worker, "imports": _imports_worker}
    print(json.dumps(workers[kind](*arguments)))
