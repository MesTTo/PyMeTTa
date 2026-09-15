"""Purpose: share Python's lossless index domain between eager and lazy rows."""

import pytest

from metta._spaces.results import Answers, Rows


@pytest.mark.parametrize("position", [0, 1, -1, -3, 3, -4])
def test_answers_accepts_index_protocol_like_rows(position):
    """Custom indices preserve positions and refusals without using int()."""
    class Index:
        def __index__(self):
            return position

    class IntOnly:
        def __int__(self):
            return 0

    eager = Rows(("value",), [(7,), (8,), (9,)])
    with Answers(iter([7, 8, 9])) as lazy:
        if -3 <= position < 3:
            assert lazy[Index()] == eager[Index()][0]
        else:
            with pytest.raises(IndexError):
                lazy[Index()]
        for invalid in (1.0, IntOnly()):
            with pytest.raises(TypeError):
                eager[invalid]
            with pytest.raises(TypeError):
                lazy[invalid]


def test_answers_slices_use_lossless_indices_without_extra_pulls():
    """Index objects in each slice position retain the ordinary lazy bound."""
    class Index:
        def __init__(self, value):
            self.value = value

        def __index__(self):
            return self.value

    pulled = []

    def source():
        for value in (7, 8, 9):
            pulled.append(value)
            yield value

    with Answers(source()) as answers:
        assert list(answers[Index(0):Index(2):Index(1)]) == [7, 8]
        assert pulled == [7, 8]
        assert list(answers[::Index(-1)]) == [9, 8, 7]
        with pytest.raises(ValueError, match="slice step cannot be zero"):
            answers[::Index(0)]
