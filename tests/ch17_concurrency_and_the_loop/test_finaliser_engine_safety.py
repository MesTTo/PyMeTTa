"""Purpose: hold the rule that no finaliser calls into Prolog.

A finaliser runs at a point no caller chooses: inside a garbage collection
pass, on any thread, possibly while that thread is already inside a crossing,
and within one reference cycle the collector finalises members in no defined
order. Three process deaths came from ignoring that -- two SIGSEGVs in
signalGCThread with a null LD, one SIGABRT on SWI's copy_record assertion over
a record another member's finaliser had already erased. The mechanism, the
cores and what was rejected are in
docs/journal/2026-09-06-finalisers-must-not-call-prolog.md.

Guarantees:
  - a released janus Term is INERT: its record id is cleared, so handing it
    back to Prolog is refused rather than reading freed memory. Without this
    the process aborts on `./src/pl-rec.c:1560: copy_record___LD: Assertion
    failed: 0` [tested:
    test_a_released_term_handed_back_to_prolog_is_refused_not_fatal;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - a Term finalised anywhere defers its record to the engine rather than
    erasing it where it stands [tested:
    test_a_finalised_term_defers_its_record_and_goes_inert;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - the next engine crossing does that deferred work, and a piece of it that
    fails does not fail the unrelated call that drained it [tested:
    test_deferred_work_is_drained_by_the_next_engine_crossing,
    test_a_failing_deferred_call_does_not_fail_the_crossing_that_drains_it;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - a lazy view dropped inside a reference cycle defers its cursor close
    instead of crossing from the collector, while an explicit close still
    closes immediately [tested:
    test_a_view_dropped_in_a_cycle_defers_its_cursor_close,
    test_an_explicit_close_still_closes_its_cursor_immediately;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - a match cursor dropped unclosed defers its close instead of crossing from
    the collector [tested:
    test_a_dropped_cursor_defers_its_close_instead_of_crossing;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - the janus private structure the release depends on is asserted, so a janus
    upgrade that moves it fails here rather than at a core dump [tested:
    test_the_janus_term_shape_the_deferred_release_depends_on;
    commit=2421d06e697daffb0797c307a798131616ebdd8e]
  - a finaliser running at INTERPRETER SHUTDOWN, after this module's globals
    are cleared, still enqueues and still says nothing [tested:
    test_a_finaliser_at_interpreter_shutdown_prints_nothing; commit=59c3cbf1bc269dfa7194f78da34497f1757a9604]
  - cursor churn leaves no new engine, even when an older engine retires;
    a replacement engine is detected by identity [tested:
    test_two_hundred_opened_and_closed_cursors_leave_no_engine_behind,
    test_the_engine_snapshot_allows_retirement_but_detects_a_replacement;
    commit=c6e1198c490a824b96f6fc6e1c0622a542917024]
  - a watch collected without close() stops its subscription and enqueues it,
    returning while another thread holds both subscription locks and making
    no engine crossing [tested:
    test_an_abandoned_watch_finaliser_neither_crosses_nor_locks;
    commit=330e04d428324008105db628ca5e0a0bbdfb55df]
  - every weakref.finalize callback in the package only hands its work over:
    to the engine's deferred queue, to its owner's queue after flagging its
    object spent, or as a ResourceWarning, so a new finaliser that crosses or
    locks fails here before it can fail at a collection [tested:
    test_every_finaliser_in_the_package_only_hands_its_work_over;
    commit=330e04d428324008105db628ca5e0a0bbdfb55df]
"""

import ast
import gc
import itertools
import os
import subprocess
import sys
import threading

import pytest

import metta._binding.runtime as _engine
from metta import S, V
from metta._binding.runtime import bridge
from metta._roots import workspace

_NAMES = itertools.count()


def _lazy_view(metta, prefix):
    """A view holding an open cursor, the shape whose finaliser closed one.

    metta.fn[...] over an effect-bearing source is the retaining route: the
    answers live in an SWI engine until the view is read or released, which is
    what makes a dropped view something the collector has to close.
    """
    name = f"{prefix}-{next(_NAMES)}"

    @metta.op(name=name, effect="writesState")
    def route(origin, destination):
        del origin, destination
        yield from ((S.paris, S.lyon), (S.lyon, S.nice))

    view = metta.fn[name](V.a, V.b)
    # The count route declines to count an effect-bearing source cheaply and
    # RETAINS the answers in an engine instead, which is what leaves a cursor
    # for a finaliser to close [source: extensions/python/metta/_spaces/execution.py:656,
    # _RetainedAnswers; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
    assert len(view) == 2
    return view


def _live_engines(metta):
    """SWI engines held by open answer cursors."""
    return metta.runtime.once("aggregate_all(count, current_engine(_), N)")["N"]


def _engine_snapshot(metta):
    """Retain the engine blobs so identity cannot be reused after retirement."""
    return metta.runtime.must(
        "findall(_Engine, current_engine(_Engine), _Engines), "
        "Engines = prolog(_Engines)"
    )["Engines"]


def _new_engines(metta, before):
    return metta.runtime.must(
        "aggregate_all(count, "
        "(current_engine(_Engine), \\+ memberchk(_Engine, Before)), N)",
        Before=before,
    )["N"]


@pytest.fixture
def janus(metta):
    """Janus through the library's own bootstrap, so the release is installed."""
    assert metta is not None
    return bridge()


@pytest.fixture(autouse=True)
def _quiet_queue(metta):
    """Leave the deferred queue as empty as it was found.

    Draining through a real crossing rather than clearing, so a test that
    deferred work does not leave it for the next test to drain and miscount.
    """
    metta.runtime.do("true")
    yield
    metta.runtime.do("true")


def _a_term(janus, tag):
    """A janus Term, which is what `prolog(X)` crosses as."""
    return janus.query_once(f"X = prolog(f({tag}))")["X"]


def test_the_janus_term_shape_the_deferred_release_depends_on(janus):
    """The private janus structure the release replaces, asserted by name.

    _install_deferred_term_release reaches into janus: it replaces a method on
    the Term class object and clears an attribute named _record. Both are
    private and neither is promised across janus releases, so this fails loudly
    at the version that moves them instead of leaving the repair silently
    inert.
    """
    assert janus.Term is not None
    assert janus._swipl is not None  # the private module the release calls
    # One class object: janus's C caches the constructor it reads from the
    # module and compares __class__ against it by identity, so a subclass would
    # stop being recognised as a record. The repair replaces the method here.
    assert janus.Term is janus.janus.Term
    term = _a_term(janus, "shape_probe")
    assert isinstance(term._record, int)  # the attribute the release clears
    assert term._record != 0  # a live Term carries its record id
    assert janus.Term.__del__.__module__ == "metta._binding.runtime", (
        "the deferred Term release is not installed on janus.Term; its __del__ "
        f"still comes from {janus.Term.__del__.__module__}"
    )


def test_a_finalised_term_defers_its_record_and_goes_inert(janus):
    """Finalising a Term queues its record and leaves nothing dangling."""
    term = _a_term(janus, "deferral_probe")
    record = term._record  # the id the release defers
    before = len(_engine._DEFERRED_WORK)  # the queue under test

    term.__del__()

    assert term._record == 0, "a released Term must not keep its record id"
    assert len(_engine._DEFERRED_WORK) == before + 1
    assert _engine._DEFERRED_WORK[-1] == (_engine._ERASE_RECORD, record)


def test_a_released_term_handed_back_to_prolog_is_refused_not_fatal(metta, janus):
    """A released Term crossing into Prolog is refused, never a dead record.

    janus 1.5.3's own __del__ clears `self.record`, an attribute nothing reads,
    where it means `self._record`, so on stock janus this same sequence hands
    PL_recorded a freed record and SWI aborts inside copy_record. The engine
    clears the attribute janus actually reads, which makes janus's own zero
    check real: py_unify_record starts `(v=PyLong_AsLongLong(r)) && ...`.
    """
    term = _a_term(janus, "released_probe")
    term.__del__()
    assert term._record == 0  # the guard that makes the crossing safe

    # The crossing must not read the freed record. Either outcome is fine; the
    # process staying alive is the point.
    try:
        janus.query_once("Y = X", {"X": term})
    except Exception:
        # A refusal is an acceptable outcome here; a crash is not.
        pass
    assert metta.runtime.once("X is 1+2")["X"] == 3, (
        "the engine survived and still answers"
    )


def test_deferred_work_is_drained_by_the_next_engine_crossing(metta, janus, monkeypatch):
    """The next crossing ERASES the record, not merely dequeues it.

    Watching the erase rather than the queue length on purpose: an earlier
    version of this test asserted only that the queue emptied, and passed
    against a drain whose erase primitive was never captured and so was None.
    The queue emptied because the item is popped before the call, and the
    failure was swallowed exactly as a finaliser's failure should be.
    """
    erased = []
    real_erase = _engine._STATE.erase_record
    assert real_erase is not None, "the release captured no erase primitive"

    def watched(record):
        erased.append(record)
        return real_erase(record)

    monkeypatch.setattr(_engine._STATE, "erase_record", watched)

    term = _a_term(janus, "drain_probe")
    record = term._record
    term.__del__()
    assert _engine._DEFERRED_WORK, "the finaliser deferred nothing"
    assert erased == [], "the finaliser erased instead of deferring"

    metta.runtime.do("true")

    assert not _engine._DEFERRED_WORK, "a crossing left deferred work behind"
    assert record in erased, "the crossing dequeued the record without erasing it"


def test_a_failing_deferred_call_does_not_fail_the_crossing_that_drains_it(metta):
    """Deferred work has no caller to raise to, so a failure stays contained."""
    _engine.defer_engine_call("metta_py_no_such_predicate_at_all", 1)

    assert metta.runtime.once("X is 2+3")["X"] == 5
    assert not _engine._DEFERRED_WORK, "the failing item was requeued"


def test_a_view_dropped_in_a_cycle_defers_its_cursor_close(metta):
    """A lazy view reachable only through a cycle closes off the collector.

    Only the cyclic collector can reclaim this, so its __del__ runs from a
    garbage collection pass. That finaliser used to call rt.do to close the
    cursor; it now hands the close over, and the queue keeps the handle alive
    until the close runs, which is the ordering the collector does not give.
    """
    gc.collect()
    baseline = _live_engines(metta)
    view = _lazy_view(metta, "cycle-probe")
    assert _live_engines(metta) == baseline + 1, "the view retained no cursor"

    cycle = [view]
    cycle.append(cycle)
    before = len(_engine._DEFERRED_WORK)
    del view, cycle
    gc.collect()

    assert len(_engine._DEFERRED_WORK) > before, (
        "the collector's finaliser crossed into Prolog instead of deferring"
    )
    # Deferred is not dropped: the next crossing does the close it deferred.
    assert _live_engines(metta) == baseline, "the deferred close never ran"


def test_an_explicit_close_still_closes_its_cursor_immediately(metta):
    """Deferral is for finalisers only; an explicit close is synchronous."""
    gc.collect()
    baseline = _live_engines(metta)
    view = _lazy_view(metta, "explicit-probe")
    assert _live_engines(metta) == baseline + 1

    view.close()

    # The handle Term's own record release is deferred like any other, and
    # correctly so; what must NOT be deferred is the cursor close itself.
    deferred_calls = [
        item for item in _engine._DEFERRED_WORK
        if item[0] == _engine._CALL_PREDICATE
    ]
    assert deferred_calls == [], (
        "an explicit close deferred its cursor instead of closing it"
    )
    assert _live_engines(metta) == baseline, "an explicit close left the cursor open"


def test_a_dropped_cursor_defers_its_close_instead_of_crossing(metta):
    """The match cursor's weakref.finalize hands its close over too.

    That finalizer caught EngineError, which reads as safe and is not: an
    EngineError is what a REFUSED crossing raises, and the fault this rule
    exists for kills the process instead of raising.
    """
    metta.run("!(add-atom &self (reap-edge a b))")
    metta.run("!(add-atom &self (reap-edge b c))")

    gc.collect()
    metta.runtime.do("true")
    baseline = _live_engines(metta)
    # stream() is the door that answers a Cursor, the object whose
    # weakref.finalize used to close the engine by crossing.
    cursor = metta.stream(S["reap-edge"](V.x, V.y))
    next(iter(cursor))
    assert _live_engines(metta) == baseline + 1, "the cursor opened no engine"

    before = len(_engine._DEFERRED_WORK)
    del cursor
    gc.collect()

    assert len(_engine._DEFERRED_WORK) > before, (
        "the cursor finalizer crossed into Prolog instead of deferring"
    )
    assert _live_engines(metta) == baseline, "the deferred close never ran"


def test_an_abandoned_watch_finaliser_neither_crosses_nor_locks(metta, monkeypatch):
    """The watch's finaliser stops delivery and enqueues, and nothing else.

    It used to call Subscription.cancel() from the collector: _TRANSACTION_LOCK,
    the registry's lock, a crossing to republish the engine's guard, two more
    for the reflection atom, and a wait on other threads' deliveries. Another
    thread holds both locks here, so a finaliser taking either would not
    return, and every crossing consults Runtime._thread_lock first, so one that
    crossed would be counted on the collecting thread.
    """
    import metta.subscribe as _subscribe
    from metta.events import _REGISTRY

    watch = metta.watch(S["abandoned-tick"](V.n))
    subscription = watch._subscription
    held = [watch]
    del watch

    locked, release = threading.Event(), threading.Event()
    crossed: list[str] = []
    runtime_type = type(metta.runtime)
    thread_lock = runtime_type._thread_lock

    def counted(runtime):
        crossed.append(threading.current_thread().name)
        return thread_lock(runtime)

    def hold_both_locks():
        with _subscribe._TRANSACTION_LOCK, _REGISTRY._lock:
            locked.set()
            release.wait()

    def collect():
        held.clear()
        gc.collect()

    holder = threading.Thread(target=hold_both_locks, name="lock-holder", daemon=True)
    collector = threading.Thread(target=collect, name="collector", daemon=True)
    monkeypatch.setattr(runtime_type, "_thread_lock", counted)
    holder.start()
    locked.wait()
    try:
        collector.start()
        # Far above a flag store and an append; a finaliser waiting on either
        # lock waits until release.set() below, whatever this bound.
        collector.join(timeout=30)
        waited_on_a_lock = collector.is_alive()
    finally:
        release.set()
        holder.join()
        collector.join()
        monkeypatch.undo()
    assert not waited_on_a_lock, "the watch's finaliser waited on a lock another thread held"
    assert "collector" not in crossed, "the watch's finaliser crossed into the engine"
    assert not subscription._active, "the abandoned subscription still delivers"
    assert subscription in _subscribe._ABANDONED
    # The next cancel(), this one's own, withdraws everything the queue holds.
    subscription.cancel()
    assert subscription not in _subscribe._ABANDONED


def test_two_hundred_opened_and_closed_cursors_leave_no_engine_behind(metta):
    """The cycle at volume, checked by engine identity.

    One opened-and-closed cursor says the close ran; two hundred say the close
    keeps running, which is the shape a per-cursor leak shows up in and a
    single pass cannot. It checks SWI ENGINES, which is what a cursor holds.
    Older engines may retire during the cycle, so count equality rejects valid
    cleanup and a count ceiling can hide a replacement leak.

    Its allocation-level twin is tests/checks/memray_plant.py, run by the
    `memray` REPORT lane: the same two hundred cursors kept alive instead of
    closed retain 19,968.0 KiB at one location against 924.6 KiB for this cycle
    [measured 2026-09-07]. This half is here because the engine table is
    exact and needs no allocator; that half is there because the bound it needs
    is measured rather than exact.
    """
    metta.run("!(add-atom &self (churn-edge a b))")
    metta.run("!(add-atom &self (churn-edge b c))")
    gc.collect()
    metta.runtime.do("true")
    baseline = _engine_snapshot(metta)

    for _ in range(200):
        cursor = metta.stream(S["churn-edge"](V.x, V.y))
        next(iter(cursor))
        cursor.close()

    assert _new_engines(metta, baseline) == 0, (
        "a closed cursor left its engine open; two hundred of them did"
    )


def test_the_engine_snapshot_allows_retirement_but_detects_a_replacement(metta):
    """Retiring an older engine cannot mask one newly left open."""
    metta.run("!(add-atom &self (snapshot-edge a b))")
    metta.run("!(add-atom &self (snapshot-edge b c))")
    first = metta.stream(S["snapshot-edge"](V.x, V.y))
    try:
        next(iter(first))
        baseline = _engine_snapshot(metta)
    finally:
        first.close()
    assert _new_engines(metta, baseline) == 0

    replacement = metta.stream(S["snapshot-edge"](V.x, V.y))
    try:
        next(iter(replacement))
        assert _new_engines(metta, baseline) == 1
    finally:
        replacement.close()
    assert _new_engines(metta, baseline) == 0


#: A cursor left open when the interpreter exits, which is the smallest program
#: that keeps a janus Term alive into module teardown.
_SHUTDOWN_PROBE = """
from metta import S, V
from metta import Space

m = Space()
m.add(S.edge(S.a, S.b))
held = m.stream(S.edge(V.x, V.y))
next(iter(held))
print("probe done")
"""


def test_a_finaliser_at_interpreter_shutdown_prints_nothing(tmp_path):
    """The last place a finaliser can still reach a torn-down module.

    CPython clears a module's globals while finalisers are still running at
    shutdown, so `_defer_record_erase` reading `_DEFERRED_WORK` as a global
    reached `None.append(...)` and printed
    `AttributeError: 'NoneType' object has no attribute 'append'` from a
    deallocator. It happens after pytest's own session ends, so no warning
    filter, no unraisable hook and no exit status could see it: only a child
    process reading its own stderr can. Both enqueue functions bind the deque
    as a default argument now, which is bound at definition time and outlives
    the globals.
    """
    program = tmp_path / "held_cursor.py"
    program.write_text(_SHUTDOWN_PROBE, encoding="utf-8")
    repository = workspace()
    result = subprocess.run(
        [sys.executable, str(program)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(tmp_path),
        env={
            **os.environ,
            "METTA_PATH": str(repository),
            "PYTHONPATH": str(repository / "extensions" / "python"),
        },
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "probe done" in result.stdout, result.stdout
    assert "Exception ignored" not in result.stderr, result.stderr


# What a finaliser may do, as statement shapes: hand a call to the engine's
# deferred queue (defer_engine_call, or the `_enqueue` its default argument
# binds), flag its object spent with a constant, or report a ResourceWarning,
# which CPython's own finalisers raise for an abandoned resource
# [source: python/cpython c554143aa15132c413b231f2c6e41f3b98de7846,
# Lib/subprocess.py:1132 Popen.__del__ and Modules/_io/fileio.c:107]. A guard
# may choose between them so long as it calls nothing.
_ENQUEUES = frozenset({"defer_engine_call", "_enqueue"})


def _hands_over(statement: ast.stmt) -> bool:
    match statement:
        case ast.Expr(value=ast.Call(func=ast.Name(id=name))) if name in _ENQUEUES:
            return True
        case ast.Assign(targets=[ast.Attribute()], value=ast.Constant()):
            return True
        case ast.Delete() | ast.Import(names=[ast.alias(name="warnings")]):
            return True
        case ast.Expr(
            value=ast.Call(
                func=ast.Attribute(value=ast.Name(id="warnings"), attr="warn"),
                args=[_, ast.Name(id="ResourceWarning"), *_],
            )
        ):
            return True
        case ast.If(test=test, body=body, orelse=orelse):
            calls = any(isinstance(node, ast.Call) for node in ast.walk(test))
            return not calls and all(map(_hands_over, [*body, *orelse]))
        case _:
            return False


def _body_without_docstring(function: ast.FunctionDef) -> list[ast.stmt]:
    first = function.body[0]
    documented = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    return function.body[1:] if documented else function.body


def test_every_finaliser_in_the_package_only_hands_its_work_over():
    """Exhaustion over every weakref.finalize the package's source makes.

    The sites are read from the source rather than listed, so a new one is in
    the census the moment it is written. Every `.finalize(` call must be
    weakref's, and its callback must be defer_engine_call itself or a
    function whose every definition in the package only hands its work over.
    """
    package = workspace() / "extensions" / "python" / "metta"
    modules = {path: ast.parse(path.read_text(encoding="utf-8")) for path in package.rglob("*.py")}
    definitions: dict[str, list[ast.FunctionDef]] = {}
    for tree in modules.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                definitions.setdefault(node.name, []).append(node)
    sites = []
    for path, tree in modules.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "finalize":
                where = f"{path.relative_to(package)}:{node.lineno}"
                receiver = node.func.value
                assert isinstance(receiver, ast.Name) and receiver.id in {"weakref", "_weakref"}, (
                    f"{where}: a .finalize( call on something other than weakref"
                )
                sites.append((where, node.args[1]))
    assert sites, "the census found no weakref.finalize at all, so it is reading the wrong tree"
    crossing = []
    for where, callback in sites:
        if isinstance(callback, ast.Name) and callback.id == "defer_engine_call":
            continue
        name = callback.id if isinstance(callback, ast.Name) else getattr(callback, "attr", None)
        bodies = definitions.get(name, [])
        if not bodies or not all(
            all(map(_hands_over, _body_without_docstring(body))) for body in bodies
        ):
            crossing.append(f"{where}: {ast.unparse(callback)}")
    assert not crossing, (
        "these finalisers do more than hand their work over; a finaliser runs at "
        "a point no caller chose, so move the work to the deferred queue "
        f"(docs/journal/2026-09-06-finalisers-must-not-call-prolog.md): {crossing}"
    )
