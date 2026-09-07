"""Purpose: metta.parallel.EnginePool, the Python-side fan-out across engines.
Guarantees:
  - every worker holds its OWN engine, asserted by distinct engine ids rather
    than by wall clock [tested test_each_worker_holds_a_distinct_engine]
  - a worker engine answers exactly what the home engine answers, over the
    core surface and under hypothesis [tested
    test_pool_agrees_with_the_home_engine,
    test_pool_agrees_with_the_home_engine_on_arbitrary_arithmetic]
  - map answers in input order however the workers finish
    [tested test_map_answers_in_input_order]
  - every failure raises, one plainly and several as one ExceptionGroup in
    INPUT order, so the error never depends on which worker lost the race
    [tested test_map_raises_every_failure_in_input_order]
  - close releases every engine and is idempotent
    [tested test_close_releases_every_engine, test_close_is_idempotent]
  - submit and close are one linearized transition: every accepted job enters
    the queue before worker stop sentinels [tested:
    test_submit_and_close_linearize_accepted_work; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import threading
import time
from concurrent.futures import Executor, as_completed, wait

import pytest

from metta import MettaError, S, V
from metta.errors import Timeout
from metta.parallel import EnginePool, imap_unordered, pool

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return metta._new_space()


@pytest.fixture()
def p():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    engine_pool = pool(workers=4)
    yield engine_pool
    engine_pool.close()


# ------------------------------------------------------------------ structure


def test_each_worker_holds_a_distinct_engine(p):
    """The whole design rests on per-worker engines, so assert the engine ids
    differ rather than inferring it from a timing win.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    # metta.subscribe.bridge is the space-to-space bridge; the Janus
    # bridge is the one in _engine.
    from metta._engine import bridge

    seen = set()
    barrier = threading.Barrier(p.workers, timeout=30)

    def engine_id(_):
        # The barrier holds every worker at once, so no worker can serve two
        # items and make one engine look like several.
        barrier.wait()
        return bridge().engine()

    ids = list(p.map(engine_id, range(p.workers)))
    seen.update(ids)
    assert len(seen) == p.workers, f"expected {p.workers} distinct engines, got {seen}"
    assert all(engine >= 0 for engine in ids)


def test_pool_reports_its_shape(p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert p.workers == 4
    assert len(p) == 4
    assert not p.closed
    assert "workers=4" in repr(p) and "live" in repr(p)


@pytest.mark.parametrize("workers", [0, -1])
def test_a_pool_needs_at_least_one_worker(workers):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="at least one worker"):
        EnginePool(workers)


@pytest.mark.parametrize("workers", ["4", True, 2.0])
def test_workers_must_be_an_int(workers):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(TypeError, match="must be an int"):
        EnginePool(workers)


# ---------------------------------------------------------------- correctness


def test_pool_agrees_with_the_home_engine(m, p):
    """The differential oracle: identical operations, identical answers."""
    m.run("(= (pool-double $x) (* $x 2))")
    m.add(S.pool_kind(S.cat, S.animal))
    m.add(S.pool_kind(S.rock, S.mineral))

    cases = {
        "value": lambda: m._one("(pool-double 21)"),
        "arith": lambda: m._one("(+ 1 (* 2 3))"),
        "query": lambda: sorted(str(r) for r in m.match(S.pool_kind(V.x, V.k))),
        "count": lambda: len(m),
        "eval": lambda: sorted(str(a) for a in m.eval("(superpose (1 2 3))")),
    }
    home = {name: run() for name, run in cases.items()}
    worker = dict(zip(cases, p.map(lambda name: cases[name](), list(cases)), strict=True))
    assert worker == home


@settings(max_examples=25)
@given(st.lists(st.integers(min_value=-500, max_value=500), min_size=1, max_size=12))
def test_pool_agrees_with_the_home_engine_on_arbitrary_arithmetic(metta, values):
    """Property: whatever the home engine answers, a worker answers too."""
    space = metta._new_space()
    home = [space._one(f"(* {v} 3)") for v in values]
    with pool(workers=3) as engine_pool:
        worker = list(engine_pool.map(lambda v: space._one(f"(* {v} 3)"), values))
    assert worker == home


def test_a_worker_can_write_and_the_home_engine_sees_it(m, p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    p.map(lambda n: m.add(S.pool_wrote(n)), range(4))
    rows = sorted(str(r.n) for r in m.match(S.pool_wrote(V.n)))
    assert rows == ["0", "1", "2", "3"]


def test_a_worker_sees_what_the_home_engine_compiled(m, p):
    """Functions compile into shared Prolog modules, so a fresh engine
    inherits them; only global-variable state is per-engine.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (pool-later $x) (+ $x 100))")
    assert list(p.map(lambda n: m._one(f"(pool-later {n})"), [1, 2])) == [101, 102]


def test_pool_composes_with_in_engine_parallel(m, p):
    """The two fan-outs nest: a pool worker may evaluate a hyperpose."""
    m.run("(= (pool-sq $x) (* $x $x))")
    branches = [f"(pool-sq {n})" for n in (1, 2, 3)]
    results = list(p.map(lambda _: sorted(str(a) for a in m.parallel(*branches)), range(4)))
    assert results == [["1", "4", "9"]] * 4


# The claim behind the 1.94x, 3.90x and 7.26x in parallel.py's header, asserted
# without a clock. A barrier is the deterministic form of "these ran at once":
# every worker has to arrive before any is released, so it can only be reached
# if the work genuinely overlaps. Serialised workers would time out on it, and
# no amount of background load can make a serialised run pass.
def test_pool_runs_work_concurrently(p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    barrier = threading.Barrier(p.workers, timeout=30)

    def arrive(_item):
        return barrier.wait()

    seats = list(p.map(arrive, range(p.workers)))
    assert sorted(seats) == list(range(p.workers))


# --------------------------------------------------------------------- order


def test_map_answers_in_input_order(p):
    """Items that finish in reverse order still answer in input order."""
    order = list(p.map(lambda n: (time.sleep((8 - n) * 0.01), n)[1], range(8)))
    assert order == list(range(8))


def test_starmap_spreads_the_arguments(m, p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert list(p.starmap(lambda a, b: m._one(f"(+ {a} {b})"), [(1, 2), (3, 4)])) == [3, 7]


def test_imap_unordered_yields_every_result(p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert sorted(imap_unordered(p, lambda n: n * 2, range(6))) == [0, 2, 4, 6, 8, 10]


# ---------------------------------------------------------- the executor face


def test_the_pool_is_an_executor_python_recognises(p):
    """Not a lookalike: Python's own words read this pool's Futures."""
    assert isinstance(p, Executor)
    futures = [p.submit(lambda n=n: n * 3) for n in range(4)]
    done, not_done = wait(futures, timeout=30)
    assert not not_done
    assert sorted(future.result() for future in done) == [0, 3, 6, 9]


def test_as_completed_yields_every_future(p):
    """Python's own completion-order reader over this pool's Futures."""
    futures = [p.submit(lambda n=n: n * n) for n in range(6)]
    assert sorted(future.result() for future in as_completed(futures, timeout=30)) == [
        0,
        1,
        4,
        9,
        16,
        25,
    ]


def test_shutdown_cancels_queued_futures():
    """cancel_futures stops what is QUEUED and leaves what a worker started."""
    engine_pool = pool(workers=1)
    gate = threading.Event()
    started = threading.Event()

    def block():
        started.set()
        return gate.wait(60)

    running = engine_pool.submit(block)
    # The one worker must be INSIDE the blocker before the drain, or the
    # blocker is still queued and cancel_futures would rightly cancel it too.
    assert started.wait(30), "the pool worker never started the blocking task"
    queued = [engine_pool.submit(lambda: 1) for _ in range(3)]
    engine_pool.shutdown(wait=False, cancel_futures=True)
    assert [future.cancelled() for future in queued] == [True, True, True]
    gate.set()
    engine_pool.shutdown(wait=True)
    assert running.result(timeout=30) is True
    assert engine_pool.closed


def test_close_is_shutdowns_other_name():
    """One teardown under two names, so a with-block and Executor agree."""
    engine_pool = pool(workers=2)
    engine_pool.close(wait=False)
    engine_pool.shutdown(wait=True)
    assert engine_pool.closed
    with pytest.raises(MettaError, match=r"closed and cannot take new work"):
        engine_pool.submit(int)


def test_map_takes_several_iterables_like_executor_map(p):
    """One iterable per argument, zipped, and an empty input answers nothing."""
    assert list(p.map(lambda a, b: a + b, [1, 2, 3], [10, 20, 30])) == [11, 22, 33]
    assert list(p.map(lambda n: n, [])) == []
    assert list(p.map(int)) == []


def test_chunksize_groups_items_into_one_task(p):
    """A chunk is one submitted task, so its items share one worker in order."""
    def seat(n):
        return threading.get_ident(), n

    whole = list(p.map(seat, range(8), chunksize=8))
    assert [n for _, n in whole] == list(range(8))
    assert len({thread for thread, _ in whole}) == 1, "one task ran on two threads"


def test_buffersize_bounds_the_work_in_flight(p):
    """buffersize=1 means one submitted task waiting at a time, so one runs."""
    lock = threading.Lock()
    live = [0]
    peak = [0]

    def watch(n):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.01)
        with lock:
            live[0] -= 1
        return n

    assert list(p.map(watch, range(6), buffersize=1)) == list(range(6))
    assert peak[0] == 1, f"buffersize=1 let {peak[0]} items run at once"


def test_a_map_timeout_stops_the_fan_out_and_leaves_the_pool_usable(p):
    """The deadline is the map's, and it cancels what has not started."""
    gate = threading.Event()
    try:
        with pytest.raises(Timeout, match=r"within 0.2 seconds") as caught:
            list(p.map(lambda _: gate.wait(60), range(3), timeout=0.2))
        assert isinstance(caught.value, TimeoutError)
    finally:
        gate.set()
    assert list(p.map(lambda n: n, range(3))) == [0, 1, 2]


def test_a_callables_own_timeout_is_not_the_maps(p):
    """A callable's own Timeout is not the map's deadline.

    metta.errors.Timeout IS a builtin TimeoutError, so the two are told
    apart by whether the future finished, never by the exception class.
    """
    def refuse(_n):
        msg = "the callable's own timeout"
        raise Timeout(msg)

    with pytest.raises(Timeout, match=r"the callable's own timeout"):
        list(p.map(refuse, range(1), timeout=30))


def test_a_fan_out_door_refuses_a_shape_it_cannot_hold(p):
    """Executor's own two keywords are validated as Executor validates them."""
    with pytest.raises(TypeError, match=r"chunksize must be an integer"):
        list(p.map(int, range(2), chunksize="two"))
    with pytest.raises(ValueError, match=r"chunksize must be > 0"):
        list(p.map(int, range(2), chunksize=0))
    with pytest.raises(TypeError, match=r"buffersize must be an integer"):
        list(p.map(int, range(2), buffersize="two"))
    with pytest.raises(ValueError, match=r"buffersize must be None or > 0"):
        list(p.map(int, range(2), buffersize=0))


def test_imap_unordered_is_a_method_and_the_function_that_names_it(p):
    """One door under two spellings, so the older free function keeps working."""
    assert sorted(p.imap_unordered(lambda n: n * 2, range(6))) == [0, 2, 4, 6, 8, 10]
    assert sorted(imap_unordered(p, lambda n: n * 2, range(6))) == [0, 2, 4, 6, 8, 10]


# -------------------------------------------------------------------- failure


def test_map_raises_every_failure_in_input_order(p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def boom(n):
        if n in (2, 5):
            msg = f"item {n}"
            raise ValueError(msg)
        return n

    with pytest.raises(ExceptionGroup) as caught:
        p.map(boom, range(8))
    assert [str(e) for e in caught.value.exceptions] == ["item 2", "item 5"]


def test_a_worker_error_does_not_kill_the_pool(p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ZeroDivisionError):
        p.map(lambda n: 1 / 0 if n else n, range(2))
    assert list(p.map(lambda n: n, range(3))) == [0, 1, 2]


def test_an_engine_error_crosses_to_the_caller(m, p):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(MettaError):
        p.map(lambda _: m.run("(this is not ("), [0])


# ------------------------------------------------------------------ lifecycle


def test_close_releases_every_engine():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    engine_pool = pool(workers=3)
    threads = list(engine_pool._started)
    engine_pool.close()
    assert engine_pool.closed
    assert not any(thread.is_alive() for thread in threads)


def test_close_is_idempotent():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    engine_pool = pool(workers=2)
    engine_pool.close()
    engine_pool.close()
    assert engine_pool.closed


def test_submit_and_close_linearize_accepted_work():
    """The accepted job precedes close's sentinel under the state lock."""
    engine_pool = pool(workers=1)
    job_reached_put = threading.Event()
    allow_job_put = threading.Event()
    accepted = []
    submit_errors: list[BaseException] = []
    original_lock = engine_pool._state_lock
    original_put = engine_pool._work.put
    closer: threading.Thread | None = None

    class ObservedLock:
        def __enter__(self):
            if threading.current_thread() is closer and original_lock.locked():
                # Fixed submit still owns the transition lock here, so let its
                # delayed queue insertion finish before close can acquire it.
                allow_job_put.set()
            original_lock.acquire()
            return self

        def __exit__(self, *_exc_info):
            original_lock.release()

    def ordered_put(item, *args, **kwargs):
        if item is None:
            result = original_put(item, *args, **kwargs)
            # In the broken ordering close reaches this sentinel while the job
            # is delayed outside the state lock, deterministically putting it last.
            allow_job_put.set()
            return result
        job_reached_put.set()
        assert allow_job_put.wait(10)
        return original_put(item, *args, **kwargs)

    engine_pool._state_lock = ObservedLock()
    engine_pool._work.put = ordered_put

    def submit() -> None:
        try:
            accepted.append(engine_pool.submit(lambda: 42))
        except BaseException as error:
            submit_errors.append(error)

    submitter = threading.Thread(target=submit)
    submitter.start()
    assert job_reached_put.wait(10)
    closer = threading.Thread(target=engine_pool.close)
    closer.start()
    submitter.join(10)
    closer.join(10)
    assert not submitter.is_alive()
    assert not closer.is_alive()
    assert submit_errors == []
    assert len(accepted) == 1
    assert accepted[0].result(timeout=10) == 42
    assert engine_pool._work.empty()


def test_closed_pool_refuses_work():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    engine_pool = pool(workers=2)
    engine_pool.close()
    with pytest.raises(MettaError, match="closed"):
        engine_pool.submit(lambda: 1)


def test_the_context_manager_closes_on_an_exception():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(RuntimeError), pool(workers=2) as engine_pool:
        saved = engine_pool
        msg = "boom"
        raise RuntimeError(msg)
    assert saved.closed


def test_metta_pool_is_the_same_pool(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with m.pool(workers=2) as engine_pool:
        assert isinstance(engine_pool, EnginePool)
        assert list(engine_pool.map(lambda n: m._one(f"(+ {n} 1)"), [1, 2])) == [2, 3]


def test_several_failures_raise_together_one_raises_plain(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def half_broken(n):
        if n % 2 == 0:
            msg = f"even {n}"
            raise ValueError(msg)
        return n

    with m.pool(workers=2) as pool:
        with pytest.raises(ExceptionGroup) as caught:
            pool.map(half_broken, [0, 1, 2, 3])
        # every failure, in INPUT order, not just the race's first
        assert [str(e) for e in caught.value.exceptions] == ["even 0", "even 2"]
        with pytest.raises(ValueError, match="even 0"):
            pool.map(half_broken, [0, 1, 3])
