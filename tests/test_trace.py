"""Purpose: the reduction trace. Events nest by depth, calls precede
their exits, exits carry answers, a failing reduction is a call with no
exit, tracing runs the source for real, and the wrap disappears after
the run so untraced calls record nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import S


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def test_trace_nests_calls_and_carries_answers(m):
    m.run("(= (tr-fact $n) (if (== $n 0) 1 (* $n (tr-fact (- $n 1)))))")
    events = m.trace("!(tr-fact 3)")
    calls = [e for e in events if e.kind == "call"]
    exits = [e for e in events if e.kind == "exit"]
    assert [str(c.term) for c in calls] == [
        "(tr-fact 3)", "(tr-fact 2)", "(tr-fact 1)", "(tr-fact 0)",
    ]
    assert [c.depth for c in calls] == [0, 1, 2, 3]
    assert str(exits[-1].term) == "(tr-fact 3)"
    assert exits[-1].answer == 6
    assert events[0].kind == "call"


def test_trace_runs_the_source_for_real(m):
    m.run("(= (tr-writer) (add-atom (context-space) (tr-mark left)))")
    m.trace("!(tr-writer)")
    assert m.query(S["tr-mark"](S.left))


def test_a_failing_reduction_is_a_call_with_no_exit(m):
    m.run("(= (tr-empty) (match &self (tr-nothing $x) $x))")
    events = m.trace("!(tr-empty)")
    kinds = [(e.kind, str(e.term)) for e in events]
    assert ("call", "(tr-empty)") in kinds
    assert ("exit", "(tr-empty)") not in kinds


def test_the_wrap_disappears_after_the_run(m):
    m.run("(= (tr-quiet $x) (+ $x 1))")
    first = m.trace("!(tr-quiet 1)")
    assert any(e.kind == "exit" and e.answer == 2 for e in first)
    assert m.run("!(tr-quiet 5)") == [[6]]
    second = m.trace("!(tr-quiet 7)")
    assert any(
        e.kind == "call" and str(e.term) == "(tr-quiet 7)" for e in second
    )
    assert not any(str(e.term) == "(tr-quiet 5)" for e in second)
