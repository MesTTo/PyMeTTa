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
from metta.vocabularies import Limit

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
    assert cut.stopped is Limit.events
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
    assert "stopped=events" in repr(cut)
    whole = m.trace("!(tr-list 2)")
    assert whole.truncated is False
    assert whole.stopped is None


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
    # And it says WHICH, because raising max_events here buys nothing: the
    # count was already ten million and the store is what ran out.
    assert cut.stopped is Limit.memory
    assert len(cut) < 10_000_000


def test_a_run_bound_stops_a_trace_the_way_it_stops_a_run(m):
    """The two kinds of bound stop different things and both now apply.

    max_events bounds the RECORDING; timeout, inferences and stack bound the
    RUN. A program can retire millions of inferences inside a handful of
    recorded events, so a recording bound is no substitute. Through 0.7.1 this
    door passed no limits at all: `with m.limits(inferences=100)` let a traced
    program run to completion while the same program under `run` stopped in
    the same scope.
    """
    from metta.errors import InferenceLimitError

    m.run("(= (loop $n) (if (> $n 0) (loop (- $n 1)) done))")

    # The control: the same bound on the same program through run(), which
    # raises, because a run has no partial answer to give back.
    with m.stats() as bounded_run, pytest.raises(InferenceLimitError):
        with m.limits(inferences=100):
            m.run("!(loop 2000)")

    with m.stats() as scoped:
        with m.limits(inferences=100):
            scoped_trace = m.trace("!(loop 2000)")

    with m.stats() as per_call:
        per_call_trace = m.trace("!(loop 2000)", inferences=100)

    for cut in (scoped_trace, per_call_trace):
        assert cut.stopped is Limit.inferences

    # Unbounded, the same program is three orders of magnitude more work, which
    # is what makes the two stops above evidence rather than coincidence.
    with m.stats() as unbounded:
        whole = m.trace("!(loop 2000)")
    assert not whole.truncated
    assert whole.stopped is None
    assert unbounded.inferences > 100 * bounded_run.inferences

    # What the bound saves is the RUN. The door's own fixed cost -- arming the
    # tracer over every name the process has registered, and unwrapping them
    # again -- sits outside the bound, twelve inferences per name [measured
    # 2026-09-07], so it is measured here and subtracted from both sides
    # rather than left to make a bounded trace look expensive: the same two
    # numbers are 4,803 against 240,016 in a fresh process and 16,795 against
    # 263,953 with two thousand more names defined.
    with m.stats() as door:
        m.trace("!(loop 0)")
    for measured in (scoped, per_call):
        assert measured.inferences - door.inferences < (
            unbounded.inferences - door.inferences
        ) / 100

    # The recording bound remains independent: it cuts events, not the run.
    prefix = m.trace("!(loop 2000)", max_events=4)
    assert prefix.stopped is Limit.events
    assert len(prefix) == 4


def test_a_run_bound_keeps_the_events_it_recorded(m):
    """A bound is a request to stop, never a request to throw the work away.

    0.7.0 settled that for the RECORDING bound and left the RUN bounds
    raising, which discarded every event with the exception. Measured
    2026-09-04 downstream on ch07's 06-peano.metta: a 2,000,000-inference
    limit answered 7,972 events on the 0.7.1 release and an
    InferenceLimitError on the tip, and the renderer reading it drew 4 frames
    where the events give 302.

    The events kept are a genuine PREFIX of the unbounded run, not a
    differently-shaped short answer, which is what makes them usable.

    The budget is half what the PROGRAM costs rather than a number written
    here, so it follows the engine instead of going stale, and half of what
    the DOOR costs is not the same thing: arming the tracer walks every name
    the process has registered and unwrapping them again is the same walk,
    twelve inferences per name [measured 2026-09-07: 12,016 in a fresh
    process, 47,943 with three thousand more names defined, against 45,600 for
    this program]. That pair is now outside the bound, so a budget of half the
    door's cost lets the whole run finish once a process is big enough, where
    before the fix it stopped inside the setup and kept no events at all --
    both directions measured under the whole suite in one process, which is
    the only configuration that reaches either.

    Tracing the base case measures the door's own cost, warm, so the
    difference is what walking 400 costs on top of it: 22,801 inferences and
    521 events at every registry size from none to three thousand extra names
    [measured 2026-09-07; the same sweep is what
    test_arming_the_tracer_is_not_charged_to_the_run_bound asserts].
    """
    m.run("(= (walk $n) (if (> $n 0) (walk (- $n 1)) done))")
    # Warm first: the first trace of a program also compiles it, and that cost
    # belongs to neither of the two measurements below.
    m.trace("!(walk 0)")
    with m.stats() as door:
        m.trace("!(walk 0)")
    with m.stats() as ran:
        whole = m.trace("!(walk 400)")
    assert not whole.truncated

    cut = m.trace("!(walk 400)", inferences=(ran.inferences - door.inferences) // 2)
    assert cut.stopped is Limit.inferences
    assert 0 < len(cut) < len(whole)
    assert [str(e.term) for e in cut] == [str(e.term) for e in whole[: len(cut)]]


def test_arming_the_tracer_is_not_charged_to_the_run_bound(m):
    """The bound is on the RUN, and arming the tracer is not the run.

    metta_trace_target/1 walks every name in the engine's arity/2 registry and
    wraps the ones a module still defines; metta_trace_end_unlocked/0 unwraps
    them again. That pair costs twelve inferences per registered NAME --
    measured 2026-09-07, a door with nothing to run cost 12,016 inferences in
    a fresh process, 35,941 with two thousand more names defined and 47,943
    with three thousand -- and it is the door's cost, not the program's.

    While the transport wrapped the whole door in metta_py_guarded/4 it came
    out of the caller's budget, so the same program under the same bound kept
    452 events in a fresh process, 306 with two thousand more names and none
    at all under the whole suite in one process: what `inferences=` did
    depended on how much else had been loaded. The names below are the
    experiment, run twice with the same budget.
    """
    m.run("(= (armed $n) (if (> $n 0) (armed (- $n 1)) done))")
    m.trace("!(armed 0)")
    with m.stats() as door:
        m.trace("!(armed 0)")
    with m.stats() as ran:
        whole = m.trace("!(armed 200)")
    budget = (ran.inferences - door.inferences) // 2
    before = m.trace("!(armed 200)", inferences=budget)
    assert before.stopped is Limit.inferences
    assert 0 < len(before) < len(whole)

    # A thousand more function names, which only the door's own walk reads.
    # The check is the DIFFERENCE rather than a ratio: the walk costs twelve
    # inferences per name wherever it starts from, and a ratio would ask the
    # names to double a door whose cost this test does not set.
    names = 1000
    m.run("\n".join(f"(= (armed-filler-{index} $x) $x)" for index in range(names)))
    with m.stats() as after_door:
        m.trace("!(armed 0)")
    assert after_door.inferences - door.inferences > names * 5

    after = m.trace("!(armed 200)", inferences=budget)
    assert len(after) == len(before)
    assert [str(e.term) for e in after] == [str(e.term) for e in before]


def test_each_bound_answers_its_prefix_and_names_itself(m):
    """One mechanism, four faces, because the remedies differ.

    A caller told only "something cut this" raises the wrong bound: asking for
    more events after the store ran out returns the same prefix at the same
    cost, and asking for more events after an inference bound runs the same
    program into the same wall.
    """
    m.run("(= (span $n) (if (> $n 0) (span (- $n 1)) done))")
    payload = " ".join(f"q{n}" for n in range(400))
    m.run("(= (heavy 0 $p) done)")
    m.run("(= (heavy $n $p) (heavy (- $n 1) $p))")

    named = {
        Limit.events: m.trace("!(span 400)", max_events=6),
        Limit.memory: m.trace(f"!(heavy 2000 ({payload}))", max_events=10_000_000),
        Limit.inferences: m.trace("!(span 4000)", inferences=40_000),
        # A recording bound far above what a fifth of a second records, so
        # the clock is what stops this one: measured 2026-09-04, 0.08s of
        # this program records 7,685 events.
        Limit.timeout: m.trace(
            "!(span 2000000)", max_events=1_000_000, timeout=0.2
        ),
    }
    for bound, cut in named.items():
        assert cut.stopped is bound, f"{bound} answered {cut.stopped}"
        assert cut.truncated is True
        assert len(cut) > 0, f"{bound} kept no events"


def test_encoding_a_bounded_trace_is_not_charged_to_the_run_bound(m):
    """The bound is on the RUN, and answering is not the run.

    Encoding the events for the wire costs more than producing them: measured
    2026-09-04 on 06-peano.metta at max_events=10,000, the traced run and
    harvest cost 686,743 inferences and the encoding cost 4,825,600, seven
    times more. Charged to the run budget, that
    trace reached its EVENT bound during the run and then died encoding
    events it had already recorded, so the caller paid the whole budget to be
    told only that the budget was gone.

    A budget comfortably above the run's own cost must therefore leave the
    recording bound in charge.
    """
    m.run("(= (brief $n) (if (> $n 0) (brief (- $n 1)) done))")
    with m.stats() as ran:
        whole = m.trace("!(brief 300)", max_events=40)
    assert whole.stopped is Limit.events

    # Twice what the whole door cost, so the RUN is nowhere near it; before
    # the bound moved inside the door this raised instead.
    cut = m.trace("!(brief 300)", max_events=40, inferences=2 * ran.inferences)
    assert cut.stopped is Limit.events
    assert len(cut) == len(whole) == 40


def test_trace_filter_preserves_depth_and_budget(m):
    """Selection precedes accounting and preserves excluded ancestor depth."""
    m.run("(= (tr-outer $x) (tr-inner $x)) (= (tr-inner $x) (+ $x 1))")
    whole = m.trace("!(tr-outer 2)")
    selected = m.trace("!(tr-outer 2)", filter=S["tr-inner"], max_events=2)
    expected = [event for event in whole if event.term.children[0] == S["tr-inner"]]
    assert selected == expected
    assert [(event.depth, event.kind) for event in selected] == [(1, "call"), (1, "exit")]
    assert selected[-1].answer == 3
    assert selected.stopped is None
    prefix = m.trace("!(tr-outer 2)", filter="tr-inner", max_events=1)
    assert prefix == selected[:1]
    assert prefix.stopped is Limit.events
    assert m.trace("!(tr-outer 2)") == whole


@pytest.mark.parametrize("names", [[], ["missing"], ["tr-outer"], ["tr-inner"],
                                   ["tr-outer", "tr-inner"], ["tr-inner", "tr-inner"]])
def test_trace_filter_is_exact_selection_of_the_whole_trace(m, names):
    """Exact-name selection agrees with the complete trace for every subset."""
    m.run("(= (tr-outer $x) (tr-inner $x)) (= (tr-inner $x) (+ $x 1))")
    whole = m.trace("!(tr-outer 4)")
    selected = m.trace("!(tr-outer 4)", filter=(Symbol(name) for name in names))
    assert selected == [event for event in whole if event.term.children[0].name in names]
    assert selected.stopped is None


def test_empty_trace_filter_still_executes_writes(m):
    """Filtering changes observation; source definitions and writes still run."""
    selected = m.trace(
        "(= (tr-write-filtered) (add-atom (context-space) (tr-filtered-mark done))) "
        "!(tr-write-filtered)",
        filter=[], max_events=1,
    )
    assert selected == []
    assert selected.stopped is None
    assert m.match(S["tr-filtered-mark"](S.done))
    assert len(m.trace("!(tr-write-filtered)")) == 2


def test_trace_filter_matches_a_function_defined_in_traced_source(m):
    """Names can be selected before the source defines the function."""
    events = m.trace("(= (tr-born $x) (+ $x 2)) !(tr-born 3)", filter="tr-born")
    assert [event.kind for event in events] == ["call", "exit"]
    assert events[-1].answer == 5


@pytest.mark.parametrize(("selection", "error", "remedy"), [
    (42, TypeError, "function Symbol"),
    ([42], TypeError, "function Symbols"),
    ("", ValueError, "nonempty"),
    ([Symbol("")], ValueError, "nonempty"),
])
def test_invalid_trace_filter_refuses_before_execution(m, selection, error, remedy):
    """Invalid names cannot execute the source before their refusal."""
    with pytest.raises(error, match=remedy):
        m.trace("!(add-atom (context-space) (tr-invalid-write done))", filter=selection)
    assert not m.match(S["tr-invalid-write"](S.done))


def test_filtered_trace_keeps_run_bounds_and_speculative_policy(m):
    """Excluding every event cannot evade run bounds or speculative rollback."""
    m.run("(= (tr-filter-loop $n) (if (> $n 0) (tr-filter-loop (- $n 1)) done))")
    cut = m.trace("!(tr-filter-loop 2000)", filter=[], inferences=100)
    assert cut == []
    assert cut.stopped is Limit.inferences
    m.run("(= (tr-filter-write) (add-atom (context-space) (tr-spec-mark done)))")
    with m.speculative():
        events = m.trace("!(tr-filter-write)", filter="tr-filter-write")
    assert len(events) == 2
    assert not m.match(S["tr-spec-mark"](S.done))


def test_trace_filter_applies_inside_hyperpose_workers(m):
    """Worker calls share the selection as well as the event buffer."""
    m.run("(= (tr-outer $x) (tr-inner $x)) (= (tr-inner $x) (+ $x 1))")
    events = m.trace("!(hyperpose ((tr-outer 1) (tr-outer 2)))", filter="tr-inner")
    assert len(events) == 4
    assert all(event.depth == 1 and event.term.children[0] == S["tr-inner"] for event in events)
    assert sorted(event.answer for event in events if event.kind == "exit") == [2, 3]
