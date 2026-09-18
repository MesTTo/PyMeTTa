"""Purpose: preserve value and caller-row identity through answer replay."""

import asyncio

import pytest

from metta._spaces.results import Answers, Rows, _AnswerItem
from metta.aio._evaluation import EvaluationView, _EvaluationGroup


def test_answer_record_survives_replay_slice_and_async_projection():
    """One record survives value reads, row reads, slicing and source failure."""
    rows = Rows(("x",), [(7,), (8,)])
    items = [_AnswerItem(7, rows[0]), _AnswerItem(8, rows[1])]
    error = ValueError("source failure")

    def source():
        yield from items
        raise error

    with Answers(source(), columns=("x",)) as answers:
        assert answers[0] == 7
        assert next(answers._items()) is items[0]
        with answers[:2] as prefix:
            assert tuple(prefix) == (7, 8)
            assert tuple(prefix._items()) == tuple(items)
            assert all(actual is expected for actual, expected in zip(prefix._items(), items, strict=True))
        group = _EvaluationGroup(None)
        group.sources = (answers,)
        assert group._cached(0, 1, rows=False) == 8
        assert group._cached(0, 1, rows=True) is rows[1]
        with pytest.raises(ValueError) as failure:
            answers[2]
        assert failure.value is error
        assert answers[0] == 7
        assert not hasattr(answers, "_row_cache"), "one answer must not occupy two independent caches"


def test_closed_answer_record_replays_both_faces_without_resuming_source():
    """Closing gives up the unpulled tail and preserves the paired cached prefix."""
    row = Rows(("x",), [(7,)])[0]
    item = _AnswerItem(7, row)
    pulls = []

    def source():
        pulls.append(0)
        yield item
        pulls.append(1)
        yield _AnswerItem(8, Rows(("x",), [(8,)])[0])

    with Answers(source(), columns=("x",)) as answers:
        assert answers[0] == 7
    assert tuple(answers) == (7,)
    assert next(answers._items()) is item
    assert tuple(answers.rows) == (row,)

    group = _EvaluationGroup(None)
    group.sources = (answers,)
    view = EvaluationView(group, 0)

    async def replay():
        assert [value async for value in view] == [7]
        assert [value async for value in view.rows] == [row]
        assert [value async for value in view] == [7]

    asyncio.run(replay())
    assert pulls == [0]


@pytest.mark.parametrize("window", [slice(None, None, -1), slice(None, None, 2), slice(-2, None)])
def test_answer_slices_keep_records_with_and_without_caller_rows(window):
    """Every slice direction preserves records, including a None answer value."""
    row = Rows(("x",), [(7,)])[0]
    with Answers([None, _AnswerItem(7, row), 8]) as answers:
        records = tuple(answers._items())
        assert tuple(answers) == (None, 7, 8)
        assert records[0].row is None
        with answers[window] as selected:
            assert tuple(selected) == (None, 7, 8)[window]
            assert all(
                actual is expected
                for actual, expected in zip(selected._items(), records[window], strict=True)
            )
