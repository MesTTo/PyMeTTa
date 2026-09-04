"""Purpose: the reduction trace. Events nest by depth, calls precede
their exits, exits carry answers, a failing reduction is a call with no
exit, a term and the source spelling it trace alike, tracing runs what
it is given for real, and the wrap disappears after the run so untraced
calls record nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from pathlib import Path

import pytest

from metta import S, Symbol

_C_EXTENSION = (
    Path(__file__).resolve().parents[4] / "examples" / "ch19-spaces-backed-by-anything" / "19-03-a-builtin-in-c"
)


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_trace_nests_calls_and_carries_answers(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_trace_takes_the_term_every_other_door_takes(m):
    """A TERM, the argument `answers`, `eval` and `match` all take. The
    tracer runs source, so the term is written and prefixed with `!`; the
    door took only text before, which made the one place you go to SEE a
    reduction the one place you had to write the program twice.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (tr-term $n) (if (== $n 0) 0 (+ $n (tr-term (- $n 1)))))")
    from_term = m.trace(S["tr-term"](3))
    from_source = m.trace("!(tr-term 3)")
    assert [(e.kind, str(e.term), e.answer) for e in from_term] == [
        (e.kind, str(e.term), e.answer) for e in from_source
    ]
    assert from_term[-1].answer == 6


def test_trace_answers_the_atom_run_answers(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Events used to cross as the term's text and be parsed back, so a
    # symbol whose spelling reads as something else arrived as something
    # else: $notvar as a variable, and a semicolon truncating the rest of
    # the term at the comment it starts.
    m.run("(= (tr-echo $x) $x)")
    for name in ("$notvar", "semi;colon", "42", "True"):
        m.add(S["tr-holds"](Symbol(name)))
        source = "!(match &self (tr-holds $v) (tr-echo $v))"
        answered = m.run(source)
        exits = [e for e in m.trace(source) if e.kind == "exit"]
        assert [e.answer for e in exits] == answered[0], name
        m.remove(S["tr-holds"](Symbol(name)))


def test_trace_names_variables_by_first_occurrence(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (tr-pair $a $b) ($b $a))")
    events = m.trace("!(tr-pair $one $two)")
    assert str(events[0].term) == "(tr-pair $_0 $_1)"


def test_trace_runs_the_source_for_real(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (tr-writer) (add-atom (context-space) (tr-mark left)))")
    m.trace("!(tr-writer)")
    assert m.match(S["tr-mark"](S.left))


def test_a_failing_reduction_is_a_call_with_no_exit(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (tr-empty) (match &self (tr-nothing $x) $x))")
    events = m.trace("!(tr-empty)")
    kinds = [(e.kind, str(e.term)) for e in events]
    assert ("call", "(tr-empty)") in kinds
    assert ("exit", "(tr-empty)") not in kinds


def test_the_wrap_disappears_after_the_run(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
    are in one test.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.register_foreign_library(
        _C_EXTENSION / "cbump.so", entry="install_cbump", names=["c-bump"]
    )
    m.run("(= (tr-foreign) (c-bump 41))")
    events = m.trace("!(tr-foreign)")
    assert [e.kind for e in events] == ["call", "exit"]
    assert events[-1].answer == 42


def test_a_bound_trace_answers_its_prefix_instead_of_raising(m):
    """Reaching max_events used to raise and discard every event with it.

    The memory was spent either way: the bound is a COUNT and an event costs
    the size of its term, so a trace that refused had already paid for the
    bound it refused at and answered nothing. Measured on
    ch22/22-03-search/02-tilepuzzle.metta, 5,000 events cost 1.38GB and a
    downstream renderer measured 100,000 above 14GB, every one of them
    raising.
    """
    m.run("(= (tr-count $n) (if (== $n 0) 0 (+ 1 (tr-count (- $n 1)))))")
    whole = m.trace("!(tr-count 20)")
    assert not whole.truncated
    assert len(whole) > 6

    cut = m.trace("!(tr-count 20)", max_events=5)
    assert cut.truncated
    assert len(cut) == 5
    assert next(event.kind for event in cut) == "call"
    # The prefix is the SAME prefix, not a different run.
    assert [str(event.term) for event in cut] == [
        str(event.term) for event in whole[:5]
    ]


def test_a_trace_is_a_list_and_says_when_it_is_a_prefix(m):
    """Every consumer iterates, indexes and lengths a trace, so it IS a list.

    `truncated` is the one thing a plain list cannot say and the one thing a
    bounded trace has to: a prefix that does not admit to being one is worse
    than the raise it replaced.
    """
    m.run("(= (tr-list $n) (if (== $n 0) 0 (+ 1 (tr-list (- $n 1)))))")
    cut = m.trace("!(tr-list 20)", max_events=3)
    assert isinstance(cut, list)
    assert len(list(cut)) == 3
    assert cut.truncated is True
    assert "truncated" in repr(cut)
    assert m.trace("!(tr-list 2)").truncated is False


def test_the_size_of_a_term_bounds_a_trace_that_a_count_does_not(m):
    """max_events cannot bound memory, because nothing bounds an event's term.

    The engine carries a second bound in cells of its own store, and both
    truncate identically so a caller never has to know which one stopped it.
    Without it, 02-tilepuzzle.metta traced at the old 1,000,000 default
    exceeded a 4GB cap and died; with it the same call stops at 4,035 events
    and 0.73GB.
    """
    payload = " ".join(f"p{n}" for n in range(400))
    m.run("(= (tr-walk 0 $p) done)")
    m.run("(= (tr-walk $n $p) (tr-walk (- $n 1) $p))")
    # A count far above the events this can produce, so only the cell budget
    # can be what stops it.
    cut = m.trace(f"!(tr-walk 2000 ({payload}))", max_events=10_000_000)
    assert cut.truncated, "the cell budget did not stop an unbounded-by-count trace"
    assert len(cut) < 10_000_000


def test_a_run_bound_stops_a_trace_the_way_it_stops_a_run(m):
    """The two bounds stop different things and both now apply.

    max_events bounds the RECORDING; timeout and inferences bound the RUN. A
    program can retire millions of inferences inside a handful of recorded
    events, so a recording bound is no substitute. Through 0.7.1 this door
    passed no limits at all: `with m.limits(inferences=100)` let a traced
    program run to completion while the same program under `run` stopped in
    the same scope.
    """
    from metta.errors import InferenceLimitError

    m.run("(= (loop $n) (if (> $n 0) (loop (- $n 1)) done))")

    # The control: the same bound on the same program through run().
    with m.stats() as bounded_run, pytest.raises(InferenceLimitError):
        with m.limits(inferences=100):
            m.run("!(loop 2000)")

    with m.stats() as scoped, pytest.raises(InferenceLimitError):
        with m.limits(inferences=100):
            m.trace("!(loop 2000)")

    with m.stats() as per_call, pytest.raises(InferenceLimitError):
        m.trace("!(loop 2000)", inferences=100)

    # Unbounded, the same program is three orders of magnitude more work, which
    # is what makes the two stops above evidence rather than coincidence.
    with m.stats() as unbounded:
        whole = m.trace("!(loop 2000)")
    assert not whole.truncated
    assert unbounded.inferences > 100 * bounded_run.inferences

    for measured in (scoped, per_call):
        assert measured.inferences < 10 * bounded_run.inferences

    # The recording bound remains independent: it cuts events, not the run.
    prefix = m.trace("!(loop 2000)", max_events=4)
    assert prefix.truncated
    assert len(prefix) == 4
