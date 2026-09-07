"""Purpose: the debugger. A breakpoint suspends a real running program and
the loop body is where it is halted; leaving the body resumes that same
execution. Stepping stops at the next reduction whether or not it carries a
breakpoint, breakpoints are a live set, an inference bound stops a resume that
would never return, and closing takes every wrapper off.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gc
import threading

import pytest

import metta as metta_package
from metta import S
from metta.errors import EngineError, InferenceLimitError, MettaError
from metta.vocabularies import EffectClass


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


@pytest.fixture()
def nested(m):
    """A two-level program: quad calls double twice."""
    m.run("(= (db-double $x) (* 2 $x))\n(= (db-quad $x) (db-double (db-double $x)))")
    return m


def test_a_breakpoint_suspends_the_program_and_resuming_carries_it_on(nested):
    """Four stops on one execution, then the answer that execution produced.

    The answers are the proof that it is ONE run rather than four: a
    breakpoint that restarted the program would answer 12 four times.
    """
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        stops = list(d)
        assert [(s.kind, str(s.term), s.answer) for s in stops] == [
            ("call", "(db-double 3)", None),
            ("exit", "(db-double 3)", 6),
            ("call", "(db-double 6)", None),
            ("exit", "(db-double 6)", 12),
        ]
        assert {s.function for s in stops} == {"db-double"}
        assert d.finished
        assert d.answers == [[12]]


def test_naming_no_breakpoint_runs_the_program_to_the_end(nested):
    """A debugger with nothing armed is a run, which is the honest reading."""
    with nested.debug(S["db-quad"](3)) as d:
        assert list(d) == []
        assert d.answers == [[12]]


def test_asking_for_the_answers_too_early_refuses_rather_than_answering_none(nested):
    """Absent is not None: an empty list would read as "it answered nothing"."""
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        next(d)
        with pytest.raises(EngineError, match="has not finished"):
            _ = d.answers


def test_step_stops_at_the_next_reduction(nested):
    """Stepping enters a function no breakpoint names, and lasts one advance.

    That is bdb's set_step: the mode selects how the program goes on from
    THIS stop, and the next stop starts from the default again.
    """
    with nested.debug(S["db-quad"](3), on=[S["db-quad"]]) as d:
        first = next(d)
        assert str(first.term) == "(db-quad 3)"
        d.step()
        # db-double carries no breakpoint; stepping reaches it anyway.
        assert str(next(d).term) == "(db-double 3)"
        # And the step did not stick: the next advance runs to a breakpoint,
        # which is db-quad's own exit.
        after = next(d)
        assert (after.kind, str(after.term)) == ("exit", "(db-quad 3)")

    # resume() cancels a step taken at the same stop.
    with nested.debug(S["db-quad"](3), on=[S["db-quad"]]) as d:
        next(d)
        d.step()
        d.resume()
        assert str(next(d).term) == "(db-quad 3)"


def test_breakpoints_can_be_changed_while_the_program_is_suspended(nested):
    """The armed set is read at every resume, so it is live.

    Adding one at a stop stops the program at it; removing one stops it
    stopping there.
    """
    with nested.debug(S["db-quad"](3), on=[S["db-quad"]]) as d:
        assert str(next(d).term) == "(db-quad 3)"
        d.breakpoints.add("db-double")
        assert str(next(d).term) == "(db-double 3)"
        d.breakpoints.discard("db-double")
        disarmed = next(d)
        assert (disarmed.kind, str(disarmed.term)) == ("exit", "(db-quad 3)")


def test_an_inference_bound_stops_a_resume_that_would_never_return(m):
    """A resume with no breakpoint ahead of it stops at the bound.

    That runaway is what a debugger needs a way out of, and inferences are
    that way: deterministic, and counted inside the engine where the work
    happens.
    """
    m.run("(= (db-spin $n) (if (> $n 0) (db-spin (- $n 1)) done))")
    with pytest.raises(InferenceLimitError):
        with m.debug(S["db-spin"](100_000), on=[S["db-nothing"]], inferences=2000) as d:
            list(d)


def test_a_debug_session_leaves_the_engine_as_it_found_it(nested):
    """The wrappers come off at close, and a dropped session is reaped.

    A session holds a wrapper on every compiled function, so one that never
    ended would slow every later run and refuse every later session.
    """
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        next(d)
    assert nested.run("!(db-quad 3)") == [[12]]
    assert len(nested.trace(S["db-quad"](3))) == 6

    dropped = nested.debug(S["db-quad"](3), on=[S["db-double"]])
    next(dropped)
    del dropped
    gc.collect()
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        assert str(next(d).term) == "(db-double 3)"


def test_one_session_at_a_time_and_a_closed_one_refuses(nested):
    """A second session, and a trace during one, are refused by name.

    They would take the same wrappers, and a closed session refuses loudly
    rather than ending a for-loop the way a finished program does.
    """
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        next(d)
        with pytest.raises(EngineError, match="already running"):
            nested.debug(S["db-quad"](3))
        with pytest.raises(EngineError, match="already running"):
            nested.trace(S["db-quad"](3))
    with pytest.raises(MettaError, match="closed"):
        next(d)


def test_an_ordinary_run_on_another_thread_is_untouched_by_a_session(nested):
    """The suspend is engine-local, so nothing else in the process stops.

    A session holds its wrappers across the host's thinking time, and every
    other execution meets them; the flag that says "suspend here" is set
    inside the debugged engine and invisible outside it.
    """
    answered = []
    with nested.debug(S["db-quad"](3), on=[S["db-double"]]) as d:
        next(d)
        thread = threading.Thread(target=lambda: answered.append(nested.run("!(db-quad 5)")))
        thread.start()
        thread.join(timeout=120)
        assert not thread.is_alive()
    assert answered == [[[20]]]


def test_a_breakpoint_inside_a_host_operation_refuses_with_its_remedy(m):
    """SWI cannot suspend an engine that is inside a callback into Prolog.

    A Python operation that evaluates MeTTa is exactly that path, so the
    breakpoint says what happened and where to put it instead rather than
    being skipped, which would make the debugger quietly incomplete.
    """
    m.run("(= (db-inner $x) (* 2 $x))")

    @m.op(name="db-through-python", effect=EffectClass.nondeterministicReadOnly)
    def through_python(term, engine: metta_package.MeTTa):
        yield engine.eval(S["db-inner"](term))

    m.run("(= (db-outer $x) (db-through-python $x))")
    with pytest.raises(EngineError, match="cannot suspend"):
        with m.debug(S["db-outer"](1), on=[S["db-inner"]]) as d:
            list(d)


def test_a_count_breakpoint_stops_at_that_event(nested):
    """at= is the third kind of breakpoint: a position rather than a name.

    Replaying a recorded run to one of its events is how a recording becomes a
    live session, and the event has no name to arm -- it is identified by
    where it is. The numbering is the trace's own, so the k-th event of
    `m.trace(src)` is where `m.debug(src, at=k)` stops, and `stop` is where
    a session opened already stopped says it landed.
    """
    events = nested.trace("!(db-quad 3)")
    for index in (0, 2, len(events) - 1):
        with nested.debug("!(db-quad 3)", at=index) as session:
            stop = next(session)
            assert (stop.seq, stop.kind) == (events[index].seq, events[index].kind)
            assert stop.term == events[index].term
            assert session.stop is stop


def test_a_negative_count_breakpoint_refuses(nested):
    """A negative count refuses rather than reading as no breakpoint at all.

    Counting from 0 has no event before the first one, and saying so beats
    running the whole program because a minus sign read as "no breakpoint".
    """
    with pytest.raises(ValueError, match="counts events from 0"):
        nested.debug("!(db-quad 3)", at=-1)
