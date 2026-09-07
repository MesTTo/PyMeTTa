"""Purpose: pin replay and one-shot ownership at the Python iterator boundary.
Guarantees:
  - py-iter gives each enumeration an independent lazy cursor over one shared
    source, including Python-API grounded values [tested:
    test_nested_py_iter_reads_form_the_cartesian_product,
    test_a_python_grounded_iterator_replays_through_the_engine;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
  - compiled Python for statements retain Python's consumptive iterator law
    [tested: test_compiled_for_keeps_one_shot_python_iteration;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
  - a grounded transport envelope owns its replay cache weakly, and concurrent
    cursors pull each source value once [tested:
    test_a_grounded_iterator_cache_dies_with_its_box,
    test_two_threads_replay_one_iterator_without_duplicate_pulls;
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3]
  - a source that RAISES is reported at the pull that raised, wearing the
    py-iter call rather than the py-atom that resolved it, and a replayable
    source reports the same failure to every later cursor [tested:
    test_a_raising_iterator_is_attributed_to_the_py_iter_that_pulled_it,
    test_a_lazily_pulled_first_item_failure_keeps_its_class_and_message,
    test_a_raising_iterator_carries_no_janus_framing,
    test_py_iter_once_reports_its_own_pull,
    test_a_failed_replay_source_reports_the_same_failure_to_every_cursor,
    test_an_iterator_of_pairs_is_not_read_as_a_terminal_failure,
    test_a_release_failure_while_closing_a_guarded_stream_propagates;
    commit=490cd97c382e5cafd0cf7b7ba2fc1aeecbf10b44].
"""  # noqa: D205  -- the contract is one continuous invariant

from __future__ import annotations

import gc
import threading
import time
import weakref

import pytest

import metta_py
from metta import Grounded, MeTTa, S
from metta.errors import EngineError

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

#: A generator expression over builtins that raises ValueError at a chosen
#: index, spelled for `py-atom`'s expression door: single quotes inside, so the
#: MeTTa string literal around it needs no escaping.
_RAISES_AT = "(int(x) for x in [{items}])"


def _raising_source(index, length=4):
    """MeTTa source for a Python generator that raises on its `index`th pull."""
    items = ",".join(
        "'oops'" if position == index else f"'{position}'" for position in range(length)
    )
    return f'(py-atom "{_RAISES_AT.format(items=items)}" Grounded)'


@given(st.lists(st.integers(min_value=-10, max_value=10), min_size=1, max_size=5))
@settings(max_examples=25, deadline=None)
def test_nested_py_iter_reads_form_the_cartesian_product(metta, values):
    """Nested enumeration replays the same source from index zero."""
    source = (
        f'!(let $it (py-atom "iter({values!r})") '
        "(let $left (py-iter $it) "
        "(let $right (py-iter $it) ($left $right))))"
    )

    assert [str(answer) for group in metta.run(source) for answer in group] == [
        f"({left} {right})" for left in values for right in values
    ]


def test_compiled_for_keeps_one_shot_python_iteration():
    """The compiler's for door consumes a Python iterator exactly once."""
    context = MeTTa()
    try:

        @context.self.define
        def replay_guard(values):
            count = 0
            for _value in values:
                count += 1
            return count

        values = iter([1, 2, 3])
        assert list(replay_guard(values)) == [3]
        assert list(replay_guard(values)) == [0]
    finally:
        context.close()


def test_a_python_grounded_iterator_replays_through_the_engine():
    """Box-backed Python API values follow the same public py-iter law."""
    context = MeTTa()
    try:
        source = Grounded(iter([1, 2, 3]))
        call = S["py-iter"](source)
        assert list(context.eval(call)) == [1, 2, 3]
        assert list(context.eval(call)) == [1, 2, 3]
    finally:
        context.close()


def test_a_grounded_iterator_cache_dies_with_its_box():
    """The weak envelope index does not turn a consumed iterator into a leak."""
    before = set(metta_py._REPLAY_CARRIERS)
    source = (value for value in range(3))
    source_ref = weakref.ref(source)
    atom = Grounded(source)
    box = atom.to_wire()[1]
    box_ref = weakref.ref(box)
    key = id(box)

    assert list(metta_py.iterate(box)) == [0, 1, 2]
    assert key in metta_py._REPLAY_CARRIERS

    del atom, box, source
    gc.collect()
    assert box_ref() is None
    assert source_ref() is None
    assert set(metta_py._REPLAY_CARRIERS) == before


def test_two_threads_replay_one_iterator_without_duplicate_pulls():
    """Concurrent cursors share every source pull and each see every value."""

    class CountingIterator:
        def __init__(self, count):
            self.count = count
            self.pulls = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.pulls == self.count:
                raise StopIteration
            value = self.pulls
            time.sleep(0.0001)
            self.pulls += 1
            return value

    source = CountingIterator(40)
    box = Grounded(source).to_wire()[1]
    start = threading.Barrier(3)
    answers = []

    def read():
        start.wait()
        answers.append(list(metta_py.iterate(box)))

    threads = [threading.Thread(target=read) for _ in range(2)]
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join()

    assert answers == [list(range(40)), list(range(40))]
    assert source.pulls == 40


def test_a_raising_iterator_is_attributed_to_the_py_iter_that_pulled_it(metta):
    """The failure names py-iter and the iterator, not the py-atom before it.

    janus's py_iter/2 reads a raising pull as an exhausted one, so the
    exception used to surface at whatever crossing ran next, wearing janus's
    own wording with a Python stack and naming no MeTTa call at all.
    """
    with pytest.raises(EngineError) as refused:
        metta.run(f"!(collapse (py-iter {_raising_source(2)}))")

    reported = str(refused.value)
    assert "Python ValueError in (py-iter" in reported
    assert "invalid literal for int() with base 10: 'oops'" in reported
    assert "generator object" in reported, "the iterator's own repr names the source"
    assert "py-atom" not in reported, "the resolution did not fail; the pull did"


def test_a_lazily_pulled_first_item_failure_keeps_its_class_and_message(metta):
    """A LAZY pull that raises immediately is not lost to CPython's own check.

    Under `once` the whole nested query returned with the Python error
    indicator still set, so `_Py_CheckFunctionResult` turned it into
    `SystemError: <built-in function apply_once> returned a result with an
    exception set` and the class, the message and the place were all gone.
    """
    with pytest.raises(EngineError) as refused:
        metta.run(f"!(once (py-iter {_raising_source(0)}))")

    reported = str(refused.value)
    assert "returned a result with an exception set" not in reported
    assert "Python ValueError in (py-iter" in reported
    assert "invalid literal for int() with base 10: 'oops'" in reported


def test_a_raising_iterator_carries_no_janus_framing(metta):
    """The report is the engine's sentence, not janus's, and nothing outlives it.

    Before the terminal pair, a raising pull under `collapse` escaped without
    ever entering metta_py_guard/2, so the caller read janus's own rendering
    with a live `Python stack:` under it and no MeTTa call above it.
    """
    with pytest.raises(EngineError) as refused:
        metta.run(f"!(collapse (py-iter {_raising_source(0)}))")

    reported = str(refused.value)
    assert "Python stack:" not in reported
    assert "metta_py.py" not in reported, "the bridge's own frames are not the caller's business"
    assert [str(answer) for group in metta.run("!((py-atom abs) -5)") for answer in group] == ["5"]


def test_py_iter_once_reports_its_own_pull(metta):
    """The consumptive door carries the same rule as the replayable one."""
    with pytest.raises(EngineError) as refused:
        metta.run(f"!(collapse (py-iter-once {_raising_source(1)}))")

    reported = str(refused.value)
    assert "Python ValueError in (py-iter-once" in reported
    assert "invalid literal for int() with base 10: 'oops'" in reported


def test_a_failed_replay_source_reports_the_same_failure_to_every_cursor():
    """A cached source remembers its failure instead of shortening.

    The source is spent once it has raised, so the alternative to remembering
    is a second enumeration reading the prefix as a complete answer. This is
    RxJava's rule for a shared sequence rather than itertools.tee's.
    """

    def source():
        yield 0
        yield 1
        msg = "the source blew up on its third pull"
        raise RuntimeError(msg)

    box = Grounded(source()).to_wire()[1]
    first = list(metta_py.iterate(box))
    second = list(metta_py.iterate(box))

    assert first[:2] == [0, 1]
    assert second[:2] == [0, 1]
    tag, failure = first[2]
    assert tag is metta_py.stream_tag()
    assert isinstance(failure, RuntimeError)
    assert str(failure) == "the source blew up on its third pull"
    assert second[2] is first[2], "one failure, replayed, not a second pull"
    assert len(first) == len(second) == 3


def test_an_iterator_of_pairs_is_not_read_as_a_terminal_failure(metta):
    """An iterator's own two-element data is data.

    A Python tuple crosses as -/2, which is the shape the reserved frame wears,
    so the reservation is the tag OBJECT rather than the shape: bridge.pl
    compares the pair's head against the private singleton metta_py holds.
    """
    answers = [
        str(answer)
        for group in metta.run('!(collapse (py-iter (py-atom "iter([(1, 2), (3, 4)])")))')
        for answer in group
    ]
    assert answers == ["((1 2) (3 4))"]


def test_a_release_failure_while_closing_a_guarded_stream_propagates():
    """A failure while CLOSING is a release failure, not a stream item.

    `yield from` delegates `close()` to the source, so a source whose `finally`
    raises does so while the guard is handling `GeneratorExit`. Yielding the
    reserved pair there would raise `RuntimeError: generator ignored
    GeneratorExit` and hide the resource failure, so the guard asks whether the
    control signal is the failure's direct context and steps aside when it is.
    """

    def source():
        try:
            yield 1
            yield 2
        finally:
            msg = "release failed"
            raise RuntimeError(msg)

    stream = metta_py._guarded(iter(source()))
    assert next(stream) == 1
    with pytest.raises(RuntimeError, match="release failed"):
        stream.close()
