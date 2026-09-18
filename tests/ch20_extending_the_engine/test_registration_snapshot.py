"""Purpose: prevent caller mutation from bypassing registry publication."""

import dataclasses

import pytest

from metta import seam


def test_registered_rows_cannot_bypass_snapshot_generation(monkeypatch):
    """The registration owns its field mapping and refuses mutable metadata."""
    monkeypatch.setattr(seam, "_LISTENERS", [])
    point = seam.point("audit-snapshot", "declaration", fields=("value",), doc="snapshot")
    try:
        supplied = {"value": object()}
        original = supplied["value"]
        row = seam._register(point, "held", "fixture", supplied)
        supplied["value"] = object()
        assert row.value is original
        with pytest.raises(TypeError):
            row.fields["value"] = object()
        for attribute, value in [("name", "other"), ("point", "other"), ("source", "other"), ("fallback", True), ("fields", {})]:
            with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
                setattr(row, attribute, value)
        assert tuple(seam._ROWS[point.name]) == (row,)
        assert row.name == "held"
        assert point.find("held") is row
        assert point.table() == {"held": row}
        assert seam.Row(point.name, "held", supplied, "fixture") != row
    finally:
        seam.withdraw(point.name)
