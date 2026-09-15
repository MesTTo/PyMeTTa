"""Purpose: restore removed registrations with their exact identity and order."""

import pytest

from metta import seam


@pytest.mark.parametrize("size", [0, 1, 2, 5])
def test_unregister_rollback_restores_each_position(monkeypatch, size):
    """Removal's inverse inserts every position, including the empty case."""
    inverses = []
    monkeypatch.setattr(seam, "_LISTENERS", [lambda point, name, undo: inverses.append(undo)])
    point = seam.point("audit-removal", "declaration", fields=("value",), doc="ordered removal")
    try:
        original = tuple(point.register(str(index), value=index) for index in range(size))
        assert point.unregister("absent") is False
        for position, row in enumerate(original):
            inverses.clear()
            assert point.unregister(row.name) is True
            assert tuple(seam._ROWS[point.name]) == original[:position] + original[position + 1:]
            assert len(inverses) == 1
            inverses[0]()
            restored = tuple(seam._ROWS[point.name])
            assert len(restored) == size
            assert all(left is right for left, right in zip(restored, original, strict=True))
    finally:
        seam.withdraw(point.name)
