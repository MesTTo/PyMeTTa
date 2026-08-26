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
      count door decline, and ``pure=True`` the one that makes it accept
      [source: bindings/python/metta/shim.pl, petta_py_eval_repeatable/2]
Guarantees:
    - the retained route replays exactly the bag the evaluating cursor
      answers, over ground rows, sparse rows, repeated and shared variables,
      duplicates, empty results, error answers and deep terms [tested:
      test_a_retained_count_replays_the_bag_the_cursor_would_have_answered]
    - a length costs one evaluation of an effect-bearing goal, whether or not
      the values are then wanted [tested:
      test_a_length_evaluates_an_effect_bearing_goal_exactly_once]
    - the values-wanted hint a count source is given picks a route and never
      an answer [tested: test_taking_an_iterator_first_does_not_change_the_answers]
    - the retained bag survives an arbitrary generated answer multiset
      [tested: test_a_generated_answer_bag_survives_both_routes]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

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


def test_a_repeatable_count_still_leaves_its_cursor_to_run(metta) -> None:
    """An effect-safe goal keeps the second evaluation the count door allows.

    A space read reaches no host operation, so the walk in
    ``petta_py_eval_repeatable/2`` accepts it, the count runs on its own
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


@settings(deadline=None, max_examples=25)
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
