"""Purpose: keep source-form position recovery linear in source length.

Guarantees:
  - position bookkeeping inspects only a constant multiple of the source while
    preserving every form's line and column [tested:
    test_position_tracking_scans_only_disjoint_source_intervals;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from operator import index
from typing import Any, SupportsIndex

from metta import _source_forms


class _ChargedSource(str):
    """A string that charges the interval inspected by count and rfind."""

    inspected: int

    def __new__(cls, value: str):
        instance = super().__new__(cls, value)
        instance.inspected = 0
        return instance

    def _charge(
        self,
        start: SupportsIndex | None,
        end: SupportsIndex | None,
    ) -> tuple[int, int]:
        begin = 0 if start is None else index(start)
        stop = len(self) if end is None else index(end)
        self.inspected += max(0, stop - begin)
        return begin, stop

    def count(
        self,
        sub: str,
        start: SupportsIndex | None = 0,
        end: SupportsIndex | None = None,
    ) -> int:
        begin, stop = self._charge(start, end)
        return super().count(sub, begin, stop)

    def rfind(
        self,
        sub: str,
        start: SupportsIndex | None = 0,
        end: SupportsIndex | None = None,
    ) -> int:
        begin, stop = self._charge(start, end)
        return super().rfind(sub, begin, stop)


class _ReaderFixture:
    """Return the engine reader rows prepared by the test."""

    def __init__(self, rows: list[list[str]]) -> None:
        self.rows = rows

    def must(self, goal: str, **inputs: Any) -> dict[str, list[list[str]]]:
        assert goal == "metta_py_read_forms(Source, Forms)"
        assert "Source" in inputs
        return {"Forms": self.rows}


def test_position_tracking_scans_only_disjoint_source_intervals(monkeypatch):
    """Two thousand forms charge a constant multiple of source length."""
    count = 2_000
    texts = [f"(p {index})" for index in range(count)]
    source = _ChargedSource("".join(f"; item\n{text}\n" for text in texts))
    rows = [["expression", text] for text in texts]
    monkeypatch.setattr(_source_forms, "runtime", lambda: _ReaderFixture(rows))

    forms = _source_forms.positioned_forms(source)

    assert len(forms) == count
    assert (forms[0].line, forms[0].column) == (2, 1)
    assert (forms[-1].line, forms[-1].column) == (count * 2, 1)
    assert source.inspected <= len(source) * 4
