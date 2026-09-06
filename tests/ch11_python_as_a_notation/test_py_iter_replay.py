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
    commit=0dc78c93461d6c7f5a83975abedf0f1a631095c3].
"""  # noqa: D205  -- the contract is one continuous invariant

from __future__ import annotations

import gc
import threading
import time
import weakref

import pytest

import metta_py
from metta import Grounded, MeTTa, S

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies


@given(st.lists(st.integers(min_value=-10, max_value=10), min_size=1, max_size=5))
@settings(max_examples=25)
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
