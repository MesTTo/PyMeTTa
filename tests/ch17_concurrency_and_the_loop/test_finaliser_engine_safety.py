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
"""

import gc
import itertools

import pytest

from metta import S, V, _engine
from metta._engine import bridge

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
    # for a finaliser to close [source: metta/_space_execution.py,
    # _RetainedAnswers; commit=2421d06e697daffb0797c307a798131616ebdd8e].
    assert len(view) == 2
    return view


def _live_engines(metta):
    """SWI engines held by open answer cursors."""
    return metta.runtime.once("aggregate_all(count, current_engine(_), N)")["N"]


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
    assert janus.Term.__del__.__module__ == "metta._engine", (
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
