"""Purpose: the reduction trace. Events nest by depth, calls precede
their exits, exits carry answers, a failing reduction is a call with no
exit, tracing runs the source for real, and the wrap disappears after
the run so untraced calls record nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from pathlib import Path

import pytest

from petta import S, Sym

_C_EXTENSION = (
    Path(__file__).resolve().parents[3] / "examples" / "integration" / "c_extension"
)


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
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


def test_trace_answers_the_atom_run_answers(m):
    # Events used to cross as the term's text and be parsed back, so a
    # symbol whose spelling reads as something else arrived as something
    # else: $notvar as a variable, and a semicolon truncating the rest of
    # the term at the comment it starts.
    m.run("(= (tr-echo $x) $x)")
    for name in ("$notvar", "semi;colon", "42", "True"):
        m.add(S["tr-holds"](Sym(name)))
        source = "!(match &self (tr-holds $v) (tr-echo $v))"
        answered = m.run(source)
        exits = [e for e in m.trace(source) if e.kind == "exit"]
        assert [e.answer for e in exits] == answered[0], name
        m.remove(S["tr-holds"](Sym(name)))


def test_trace_names_variables_by_first_occurrence(m):
    m.run("(= (tr-pair $a $b) ($b $a))")
    events = m.trace("!(tr-pair $one $two)")
    assert str(events[0].term) == "(tr-pair $_0 $_1)"


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


@pytest.mark.skipif(
    not (_C_EXTENSION / "cbump.so").is_file(),
    reason="cbump.so is not built; a C toolchain is not an engine requirement",
)
def test_a_foreign_predicate_does_not_break_tracing(m):
    """clause/3 refuses a foreign predicate by raising rather than failing, and
    the trace walks every registered arity looking for tracked clauses. One C
    extension registered anywhere in the process used to make every trace in
    it raise, this one included, which is why the registration and the trace
    are in one test."""
    m.register_foreign_library(
        _C_EXTENSION / "cbump.so", entry="install_cbump", names=["c-bump"]
    )
    m.run("(= (tr-foreign) (c-bump 41))")
    events = m.trace("!(tr-foreign)")
    assert [e.kind for e in events] == ["call", "exit"]
    assert events[-1].answer == 42
