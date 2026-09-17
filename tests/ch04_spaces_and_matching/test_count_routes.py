"""Purpose: a differential between the three routes a lazy view can take to
its answers, so a count can never change what the view says.

An ``Answers`` view reaches its answers one of three ways. Iterating without
asking for a length opens the evaluating cursor and pulls it. Asking for a
length first sends the goal to the engine's count door, which either counts a
repeatable goal in a second evaluation and leaves the cursor to run later, or
declines and instead evaluates ONCE, holding the answers in the engine for the
cursor to replay. Every test here runs the same program through the routes and
compares answer BAGS: order is unspecified in MeTTa, multiplicity is not.
Assumes:
    - ``metta.op(effect="writesState")`` is the classification that makes the
      count door decline, and ``effect="pureStructural"`` makes it accept
      [source: extensions/python/metta/_binding/evaluation.pl:metta_py_repeatable/2; commit=8358dfc233bf299bb23eceddd94593a62372fe4b]
Guarantees:
    - the retained route replays exactly the bag the evaluating cursor
      answers, over ground rows, sparse rows, repeated and shared variables,
      duplicates, empty results, error answers and deep terms [tested:
      test_a_retained_count_replays_the_bag_the_cursor_would_have_answered]
    - a length costs one evaluation of an effect-bearing goal, whether or not
      the values are then wanted [tested:
      test_a_length_evaluates_an_effect_bearing_goal_exactly_once]
    - the values-wanted hint a count source is given picks a route and never
      an answer [tested: test_taking_an_iterator_first_does_not_change_the_answers,
      test_list_materializes_a_match_without_a_second_query]
    - the retained bag survives an arbitrary generated answer multiset
      [tested: test_a_generated_answer_bag_survives_both_routes]
    - a repeatable guard is counted by the engine rather than declined
      [tested: test_a_guarded_length_counts_inside_the_engine; commit=689745c3bb9ef9a36b5427bb3e7289a69da9b71b]
    - inspecting an Answers iterator never delays its engine release through
      a frame reference cycle [tested:
      test_iteration_does_not_delay_answer_finalization_in_a_frame_cycle,
      test_function_call_does_not_delay_answer_finalization_in_a_frame_cycle;
      commit=853623455cdb02fe0afc1c815023a45c4a0eb989]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import gc
import itertools
from collections import Counter
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from metta import S, V

_NAMES = itertools.count()


def unique(prefix: str) -> str:
    """A fresh MeTTa head, because the session space outlives one test."""
    return f"{prefix}-{next(_NAMES)}"


def bag(view: Any) -> Counter:
    """The answer multiset, rendered so unhashable atoms still compare."""
    return Counter(str(answer) for answer in iter(view))


def cursor_bag(call) -> Counter:
    """Route 1: pull the evaluating cursor, never asking for a length.

    ``iter`` rather than ``list``, because ``list`` consults ``__len__`` for
    its length hint and would take the counting route instead.
    """
    return bag(call())


def counted_bag(call) -> tuple[int, Counter]:
    """Route 2 and 3: ask for the length first, then read the values."""
    view = call()
    counted = len(view)
    return counted, bag(view)


def both_routes_agree(call) -> Counter:
    """Run one program both ways and return the bag they agree on."""
    first = cursor_bag(call)
    counted, second = counted_bag(call)
    assert second == first, f"counted route {second} != cursor route {first}"
    assert counted == sum(first.values()), (
        f"len() said {counted}, the bag holds {sum(first.values())}"
    )
    return first


def two_city_route(metta, prefix: str) -> str:
    """Register the effectful two-answer source used by lifecycle probes."""
    name = unique(prefix)

    @metta.op(name=name, effect="writesState")
    def route(origin, destination):
        del origin, destination
        yield from ((S.paris, S.lyon), (S.lyon, S.nice))

    return name


def live_engines(metta) -> int:
    """Count the SWI engines held by open answer cursors."""
    return metta.runtime.once("aggregate_all(count, current_engine(_), N)")["N"]


def test_a_retained_count_replays_the_bag_the_cursor_would_have_answered(metta) -> None:
    """Every adversarial row shape answers one bag whichever route reads it."""
    effectful = unique("route-effectful")
    rows = [
        (S.paris, S.lyon),
        (S.paris, S.lyon),
        (S.lyon, S.nice),
        (S.paris, S.paris),
    ]

    @metta.op(name=effectful, effect="writesState")
    def route(origin, destination):
        del origin, destination
        yield from rows

    # Ground both ways, one way, neither way, and the repeated-variable call
    # whose two positions must agree.
    assert both_routes_agree(lambda: metta.fn[effectful](V.a, V.b)).total() == 4
    assert both_routes_agree(lambda: metta.fn[effectful](S.paris, V.b)).total() == 3
    assert both_routes_agree(lambda: metta.fn[effectful](V.a, S.lyon)).total() == 2
    assert both_routes_agree(lambda: metta.fn[effectful](S.paris, S.lyon)).total() == 2
    assert both_routes_agree(lambda: metta.fn[effectful](S.rome, S.nice)).total() == 0
    assert both_routes_agree(lambda: metta.fn[effectful](V.same, V.same)).total() == 1

    sparse = unique("route-sparse")

    @metta.op(name=sparse, effect="writesState")
    def sparse_route(origin, destination):
        del origin, destination
        yield {"origin": S.paris}
        yield {"destination": S.nice}
        yield {"origin": S.paris}

    assert both_routes_agree(lambda: metta.fn[sparse](V.a, V.b)).total() == 3
    assert both_routes_agree(lambda: metta.fn[sparse](S.paris, V.b)).total() == 3

    deep = unique("route-deep")

    @metta.op(name=deep, effect="writesState")
    def deep_answers(depth):
        """Nested answers, the shape whose encoding costs by term size."""
        for width in range(depth):
            answer = S.z
            for _ in range(width):
                answer = S.s(answer)
            yield answer

    assert both_routes_agree(lambda: metta.fn[deep](5)).total() == 5

    empty = unique("route-empty")

    @metta.op(name=empty, effect="writesState")
    def no_answers(anything):
        del anything
        return
        yield  # pragma: no cover  -- the yield is what makes this a generator

    assert both_routes_agree(lambda: metta.fn[empty](1)).total() == 0

    failing = unique("route-failing")

    @metta.op(name=failing, effect="writesState")
    def half_failing(count):
        """Two answers and then a refusal, kept as the stream's last answer."""
        for index in range(count):
            if index == 2:
                msg = "the third answer refuses"
                raise ValueError(msg)
            yield index

    metta.on_error(failing, S[failing](V.count), "keep")
    assert both_routes_agree(lambda: metta.fn[failing](4)).total() == 3


def test_a_length_evaluates_an_effect_bearing_goal_exactly_once(metta) -> None:
    """One length is one evaluation, with or without a later value demand."""
    name = unique("route-once")
    fired: list[int] = []

    @metta.op(name=name, effect="writesState")
    def counted(limit):
        for index in range(limit):
            fired.append(index)
            yield index

    length_only = metta.fn[name](3)
    assert len(length_only) == 3
    assert fired == [0, 1, 2]

    fired.clear()
    both = metta.fn[name](3)
    assert len(both) == 3
    assert [str(answer) for answer in both] == ["0", "1", "2"]
    assert fired == [0, 1, 2], "the values must replay, not re-evaluate"

    fired.clear()
    assert len(list(metta.fn[name](3))) == 3
    assert fired == [0, 1, 2], "list()'s length hint must not double the effect"



def test_list_of_an_evaluation_view_costs_one_pass(metta) -> None:
    """The idiomatic spelling has to be the fast one.

    `list(view)` asks for an iterator BEFORE its length hint, which is exactly
    how a count source knows the values are wanted. The match door has always
    tested that hint first. The evaluation door asked its separate-engine
    count first and tested the hint after, then returned the number it had
    already paid for, so `list()` bought a count AND drained the cursor:
    90,399 inferences against 8,563 for the equivalent comprehension over 400
    answers, 10.6x [measured 2026-09-05].

    The RATIO is what this pins rather than either number, because both sides
    move together with the engine. Every other test in this file measures
    effects, which is why none of them saw this: the doors answered the same
    values at very different cost, and the file's own note said that cost was
    a corpus lane's business. No lane exercised list() over an evaluation
    view.
    """
    name = unique("route-listcost")
    literals = " ".join(str(index) for index in range(400))
    metta.run(f"(= ({name}) (superpose ({literals})))")

    def cost(drain) -> int:
        with metta.stats() as stats:
            drain(metta.answers(f"({name})"))
        return stats.inferences

    cost(list)  # the first evaluation compiles; neither arm should carry that
    comprehension = min(
        cost(lambda view: [answer for answer in view])  # noqa: C416 -- the two spellings are the arms; rewriting one into the other erases the comparison
        for _ in range(3)
    )
    materialized = min(cost(list) for _ in range(3))

    assert materialized <= comprehension * 1.25, (
        f"list(view) cost {materialized} inferences against {comprehension} "
        f"for the comprehension over the same answers; the values-wanted hint "
        f"is being tested after the count it exists to avoid"
    )


def test_a_repeatable_count_still_leaves_its_cursor_to_run(metta) -> None:
    """An effect-safe goal keeps the second evaluation the count door allows.

    A space read reaches no host operation, so the walk in
    ``metta_py_repeatable/2`` accepts it, the count runs on its own
    engine, and the cursor is still unopened afterwards. Nothing is retained,
    which is why the later pull sees a row written in between.
    """
    head = unique("route-readable")
    fact = unique("route-fact")
    metta.run(f"(= ({head}) (match &self ({fact} $value) $value))")
    metta += S[fact](1)

    view = metta.fn[head]()
    assert len(view) == 1
    metta += S[fact](2)

    # Nothing was held, so this pull is the goal's own evaluation and reads
    # the row written after the count.
    assert bag(view) == Counter({"1": 1, "2": 1})


def test_taking_an_iterator_first_does_not_change_the_answers(metta) -> None:
    """The values-wanted hint picks a route and nothing else.

    ``list(view)`` asks for an iterator before it asks for a length hint, and
    a count source may use that to skip holding answers the caller is about
    to read. Whether it does or not, the length and the bag are the same, and
    an effect fires once. What the hint IS worth is a cost the corpus lane
    measures, not a different answer.
    """
    name = unique("route-hint")
    fired: list[int] = []

    @metta.op(name=name, effect="writesState")
    def hinted(limit):
        for index in range(limit):
            fired.append(index)
            yield index

    hinted_first = metta.fn[name](3)
    rows = iter(hinted_first)
    assert len(hinted_first) == 3
    assert [str(answer) for answer in rows] == ["0", "1", "2"]
    assert fired == [0, 1, 2]

    fired.clear()
    counted_first = metta.fn[name](3)
    assert len(counted_first) == 3
    assert [str(answer) for answer in counted_first] == ["0", "1", "2"]
    assert fired == [0, 1, 2]


def test_list_materializes_a_match_without_a_second_query(metta, monkeypatch) -> None:
    """A caller already reading rows does not pre-count the same match."""
    metta.add(S["route-list-row"](1))
    runtime = metta.runtime
    original = type(runtime).apply_must
    counts: list[str] = []

    def observe(self, predicate, *inputs):
        if predicate == "metta_py_query_count_if_repeatable":
            counts.append(predicate)
        return original(self, predicate, *inputs)

    monkeypatch.setattr(type(runtime), "apply_must", observe)

    materialized = list(metta.match(S["route-list-row"](V.value)))
    assert [row.value for row in materialized] == [1]
    assert counts == [], "list() must use its one materializing query"

    assert len(metta.match(S["route-list-row"](V.value))) == 1
    assert counts == ["metta_py_query_count_if_repeatable"]


@settings(max_examples=25)
@given(
    st.lists(
        st.integers(min_value=-6, max_value=6),
        min_size=0,
        max_size=12,
    )
)
def test_a_generated_answer_bag_survives_both_routes(metta, answers) -> None:
    """Any answer multiset, duplicates included, reads the same either way."""
    name = unique("route-fuzz")

    @metta.op(name=name, effect="writesState")
    def generated(seed):
        del seed
        yield from answers

    agreed = both_routes_agree(lambda: metta.fn[name](0))
    assert agreed == Counter(str(value) for value in answers)


def test_a_view_releases_its_cursor_on_request_not_only_on_collection(metta) -> None:
    """`close()` and the `with` form, which the other resource-owning type had.

    A lazy view owns an engine cursor. `Space` has said so from the start, with
    `drop()` and the `with` form, and the ASYNC cursor says so too with
    `aclose()` and its async context manager; the synchronous view had only a
    finalizer. Being only a finalizer is the defect: `__del__` runs during
    interpreter shutdown with module globals already cleared, which is how an
    abandoned cursor printed "Exception ignored ... catching classes that do
    not inherit from BaseException" out of a torn-down module [measured
    2026-08-31].
    """
    name = two_city_route(metta, "route-closed")

    gc.collect()
    before = live_engines(metta)

    # Abandoned part-way, then closed by hand rather than by the collector.
    view = metta.answers(S[name](V.origin, V.destination))
    next(iter(view))
    assert live_engines(metta) > before, "a pulled view holds a cursor"
    view.close()
    assert live_engines(metta) == before, "close() gives it back"
    view.close()  # twice is a no-op, as drop() is

    # Answers already pulled stay readable: they are cached values, not engine
    # state, so closing gives up only what was never pulled.
    assert view[0] is not None

    # And the with form is the same act, scoped.
    with metta.answers(S[name](V.origin, V.destination)) as scoped:
        next(iter(scoped))
        assert live_engines(metta) > before
    assert live_engines(metta) == before, "leaving the block gives it back"


def test_iteration_does_not_delay_answer_finalization_in_a_frame_cycle(metta) -> None:
    """Dropping an iterated view closes its engine without cyclic collection.

    Answers inspects its caller to record ordering lint. Keeping the current
    frame in that method also kept ``self`` alive, so a started engine cursor
    survived ordinary reference-counted finalization and closed only when the
    cyclic collector happened to run.
    """
    name = two_city_route(metta, "route-frame-cycle")

    gc.collect()
    before = live_engines(metta)
    gc.disable()
    try:
        view = metta.answers(S[name](V.origin, V.destination))
        next(iter(view))
        assert live_engines(metta) == before + 1, (
            "the partial iteration must open a cursor"
        )
        del view
        assert live_engines(metta) == before, (
            "ordinary finalization must close the cursor"
        )
    finally:
        gc.enable()
        gc.collect()


def test_function_call_does_not_delay_answer_finalization_in_a_frame_cycle(
    metta,
) -> None:
    """A bound call does not retain the lazy result it has returned."""
    name = two_city_route(metta, "route-call-frame-cycle")

    gc.collect()
    before = live_engines(metta)
    gc.disable()
    try:
        view = metta.fn[name](V.origin, V.destination)
        next(iter(view))
        assert live_engines(metta) == before + 1, (
            "the partial iteration must open a cursor"
        )
        del view
        assert live_engines(metta) == before, (
            "the completed call frame must release its result"
        )
    finally:
        gc.enable()
        gc.collect()


def test_a_counted_view_releases_its_engine_when_it_is_dropped(metta) -> None:
    """A counted view nobody iterates releases the cursor its count retained.

    The retaining route holds the whole answer bag in an SWI engine so the
    values cost no second evaluation of an effect-bearing goal. A generator
    that was never started runs no finally block, so closing the view closed
    nothing: measured 2026-08-30, current_engine/1 still counted the engine
    after del and gc.collect(), and metta_py_cursor_next still answered from
    the abandoned handle.
    """
    name = two_city_route(metta, "route-dropped")

    gc.collect()  # an earlier view collected mid-test would move the count
    before = live_engines(metta)
    view = metta.fn[name](V.a, V.b)
    assert len(view) == 2
    assert live_engines(metta) == before + 1, "the declined count retained a cursor"
    del view
    gc.collect()
    assert live_engines(metta) == before


def test_a_guarded_length_counts_inside_the_engine(metta, monkeypatch) -> None:
    """A repeatable guard keeps ``len`` on the engine-side count.

    From 2026-09-02 until 98540fdb2 the count door declined every guard: its
    conjunction builder was undefined where the door called it, and the
    evaluator's catch-all read the missing procedure as "not repeatable", so
    every guarded length fell back to the cursor route, whose work runs in an
    SWI engine the caller's inference counter cannot see.
    """
    metta.add(*(S["route-guarded-row"](value) for value in range(6)))
    runtime = metta.runtime
    original = type(runtime).apply_must
    answers: list[Any] = []

    def observe(self, predicate, *inputs):
        result = original(self, predicate, *inputs)
        if predicate == "metta_py_query_count_if_repeatable":
            answers.append(result)
        return result

    monkeypatch.setattr(type(runtime), "apply_must", observe)
    guarded = metta.match(S["route-guarded-row"](V.value), where=S[">="](V.value, 3))
    assert len(guarded) == 3
    assert [int(answer[0]) for answer in answers] == [3], "a repeatable guard is counted, not declined"
