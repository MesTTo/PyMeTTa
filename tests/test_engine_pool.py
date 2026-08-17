"""Purpose: petta.parallel.EnginePool, the Python-side fan-out across engines.
Guarantees:
  - every worker holds its OWN engine, asserted by distinct engine ids rather
    than by wall clock [tested test_each_worker_holds_a_distinct_engine]
  - a worker engine answers exactly what the home engine answers, over the
    core surface and under hypothesis [tested
    test_pool_agrees_with_the_home_engine,
    test_pool_agrees_with_the_home_engine_on_arbitrary_arithmetic]
  - map answers in input order however the workers finish
    [tested test_map_answers_in_input_order]
  - the first failure in INPUT order is the one raised, so the error does not
    depend on which worker lost the race
    [tested test_map_raises_the_first_failure_in_input_order]
  - close releases every engine and is idempotent
    [tested test_close_releases_every_engine, test_close_is_idempotent]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import threading
import time

import pytest

from petta import PettaError, S, V
from petta.parallel import EnginePool, imap_unordered, pool

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


@pytest.fixture()
def m(metta):
    return metta.fresh_space()


@pytest.fixture()
def p():
    engine_pool = pool(workers=4)
    yield engine_pool
    engine_pool.close()


# ------------------------------------------------------------------ structure


def test_each_worker_holds_a_distinct_engine(p):
    """The whole design rests on per-worker engines, so assert the engine ids
    differ rather than inferring it from a timing win."""
    # petta.bridge is subscribe.bridge(source, pattern, target); the janus
    # bridge is the one in _engine.
    from petta._engine import bridge

    seen = set()
    barrier = threading.Barrier(p.workers, timeout=30)

    def engine_id(_):
        # The barrier holds every worker at once, so no worker can serve two
        # items and make one engine look like several.
        barrier.wait()
        return bridge().engine()

    ids = p.map(engine_id, range(p.workers))
    seen.update(ids)
    assert len(seen) == p.workers, f"expected {p.workers} distinct engines, got {seen}"
    assert all(engine >= 0 for engine in ids)


def test_pool_reports_its_shape(p):
    assert p.workers == 4
    assert len(p) == 4
    assert not p.closed
    assert "workers=4" in repr(p) and "live" in repr(p)


@pytest.mark.parametrize("workers", [0, -1])
def test_a_pool_needs_at_least_one_worker(workers):
    with pytest.raises(ValueError, match="at least one worker"):
        EnginePool(workers)


@pytest.mark.parametrize("workers", ["4", True, 2.0])
def test_workers_must_be_an_int(workers):
    with pytest.raises(TypeError, match="must be an int"):
        EnginePool(workers)


# ---------------------------------------------------------------- correctness


def test_pool_agrees_with_the_home_engine(m, p):
    """The differential oracle: identical operations, identical answers."""
    m.run("(= (pool-double $x) (* $x 2))")
    m.add(S.pool_kind(S.cat, S.animal))
    m.add(S.pool_kind(S.rock, S.mineral))

    cases = {
        "value": lambda: m.value("(pool-double 21)"),
        "arith": lambda: m.value("(+ 1 (* 2 3))"),
        "query": lambda: sorted(str(r) for r in m.query(S.pool_kind(V.x, V.k))),
        "count": lambda: m.count(),
        "eval": lambda: sorted(str(a) for a in m.eval("(superpose (1 2 3))")),
    }
    home = {name: run() for name, run in cases.items()}
    worker = dict(zip(cases, p.map(lambda name: cases[name](), list(cases)), strict=True))
    assert worker == home


@settings(max_examples=25, deadline=None)
@given(st.lists(st.integers(min_value=-500, max_value=500), min_size=1, max_size=12))
def test_pool_agrees_with_the_home_engine_on_arbitrary_arithmetic(metta, values):
    """Property: whatever the home engine answers, a worker answers too."""
    space = metta.fresh_space()
    home = [space.value(f"(* {v} 3)") for v in values]
    with pool(workers=3) as engine_pool:
        worker = engine_pool.map(lambda v: space.value(f"(* {v} 3)"), values)
    assert worker == home


def test_a_worker_can_write_and_the_home_engine_sees_it(m, p):
    p.map(lambda n: m.add(S.pool_wrote(n)), range(4))
    rows = sorted(str(r.n) for r in m.query(S.pool_wrote(V.n)))
    assert rows == ["0", "1", "2", "3"]


def test_a_worker_sees_what_the_home_engine_compiled(m, p):
    """Functions compile into shared Prolog modules, so a fresh engine
    inherits them; only global-variable state is per-engine."""
    m.run("(= (pool-later $x) (+ $x 100))")
    assert p.map(lambda n: m.value(f"(pool-later {n})"), [1, 2]) == [101, 102]


def test_pool_composes_with_in_engine_parallel(m, p):
    """The two fan-outs nest: a pool worker may evaluate a hyperpose."""
    m.run("(= (pool-sq $x) (* $x $x))")
    branches = [f"(pool-sq {n})" for n in (1, 2, 3)]
    results = p.map(lambda _: sorted(str(a) for a in m.parallel(*branches)), range(4))
    assert results == [["1", "4", "9"]] * 4


# The claim behind the 1.94x, 3.90x and 7.26x in parallel.py's header, asserted
# without a clock. A barrier is the deterministic form of "these ran at once":
# every worker has to arrive before any is released, so it can only be reached
# if the work genuinely overlaps. Serialised workers would time out on it, and
# no amount of background load can make a serialised run pass.
def test_pool_runs_work_concurrently(p):
    barrier = threading.Barrier(p.workers, timeout=30)

    def arrive(_item):
        return barrier.wait()

    seats = p.map(arrive, range(p.workers))
    assert sorted(seats) == list(range(p.workers))


# --------------------------------------------------------------------- order


def test_map_answers_in_input_order(p):
    """Items that finish in reverse order still answer in input order."""
    order = p.map(lambda n: (time.sleep((8 - n) * 0.01), n)[1], range(8))
    assert order == list(range(8))


def test_starmap_spreads_the_arguments(m, p):
    assert p.starmap(lambda a, b: m.value(f"(+ {a} {b})"), [(1, 2), (3, 4)]) == [3, 7]


def test_imap_unordered_yields_every_result(p):
    assert sorted(imap_unordered(p, lambda n: n * 2, range(6))) == [0, 2, 4, 6, 8, 10]


# -------------------------------------------------------------------- failure


def test_map_raises_the_first_failure_in_input_order(p):
    def boom(n):
        if n in (2, 5):
            raise ValueError(f"item {n}")
        return n

    with pytest.raises(ValueError, match="item 2"):
        p.map(boom, range(8))


def test_a_worker_error_does_not_kill_the_pool(p):
    with pytest.raises(ZeroDivisionError):
        p.map(lambda n: 1 / 0 if n else n, range(2))
    assert p.map(lambda n: n, range(3)) == [0, 1, 2]


def test_an_engine_error_crosses_to_the_caller(m, p):
    with pytest.raises(PettaError):
        p.map(lambda _: m.run("(this is not ("), [0])


# ------------------------------------------------------------------ lifecycle


def test_close_releases_every_engine():
    engine_pool = pool(workers=3)
    threads = list(engine_pool._started)
    engine_pool.close()
    assert engine_pool.closed
    assert not any(thread.is_alive() for thread in threads)


def test_close_is_idempotent():
    engine_pool = pool(workers=2)
    engine_pool.close()
    engine_pool.close()
    assert engine_pool.closed


def test_closed_pool_refuses_work():
    engine_pool = pool(workers=2)
    engine_pool.close()
    with pytest.raises(PettaError, match="closed"):
        engine_pool.submit(lambda: 1)


def test_the_context_manager_closes_on_an_exception():
    with pytest.raises(RuntimeError), pool(workers=2) as engine_pool:
        saved = engine_pool
        raise RuntimeError("boom")
    assert saved.closed


def test_metta_pool_is_the_same_pool(m):
    with m.pool(workers=2) as engine_pool:
        assert isinstance(engine_pool, EnginePool)
        assert engine_pool.map(lambda n: m.value(f"(+ {n} 1)"), [1, 2]) == [2, 3]
