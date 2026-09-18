"""Purpose: retain every inverse failure while attempting every cleanup."""

import pytest

from metta import seam


@pytest.mark.parametrize("failures", [(), (0,), (1,), (0, 1)])
def test_inverse_sequence_attempts_every_action(failures):
    """The two existing inverse positions preserve order and all failures."""
    visited = []
    errors = [ValueError("first inverse"), KeyboardInterrupt("second inverse")]

    def action(position):
        def undo():
            visited.append(position)
            if position in failures:
                raise errors[position]
        return undo

    inverse = seam._both(action(0), action(1))
    caught = []
    try:
        inverse()
    except BaseException as error:
        caught = list(error.exceptions) if isinstance(error, BaseExceptionGroup) else [error]
    assert visited == [0, 1]
    assert caught == [errors[index] for index in failures]
