"""Purpose: source positions for the engine's own reader. The reader
answers each form's KIND and verbatim TEXT (metta_py_read_forms); between
forms the grammar allows only whitespace and ;-comments, so a single
deterministic walk recovers every form's line and column exactly, with
no search and no engine change: the consumers that want positions pay
here, and the hot compile path pays nothing, SWI's own
subterm_positions philosophy.
Assumes:
  - form texts are verbatim slices of the source in source order, and a
    runnable form's text excludes its leading ! [tested
    test_positioned_forms_recover_exact_lines]
Guarantees:
  - a locator/reader disagreement raises instead of guessing [tested
    test_a_locator_mismatch_refuses]
  - line and column tracking scans disjoint source intervals, so F forms in N
    characters take theta(N), not theta(N*F) [tested:
    test_position_tracking_scans_only_disjoint_source_intervals;
    commit=aa02d6c674b1e86eec5ddf32d111400df8f9e4b4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from typing import NamedTuple

from ._engine import runtime
from .errors import MettaError


class SourceForm(NamedTuple):
    """One top-level form: the parser's kind, its verbatim text, and the
    1-based line and column its first character sits at.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    kind: str
    text: str
    line: int
    column: int


def _skip_between(source: str, cursor: int) -> int:
    """Advance past what the grammar allows between forms: whitespace and
    ;-comments to end of line.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    length = len(source)
    while cursor < length:
        ch = source[cursor]
        if ch.isspace():
            cursor += 1
        elif ch == ";":
            newline = source.find("\n", cursor)
            cursor = length if newline < 0 else newline + 1
        else:
            break
    return cursor


# CPython's untokenizer likewise carries the previous row and column between
# adjacent tokens instead of re-deriving each position from a source prefix:
# https://github.com/python/cpython/blob/3daa7f8258fa21931e7655de66160b05afcfc8c9/Lib/tokenize.py#L168-L182
def _advance_position(
    source: str,
    start: int,
    end: int,
    line: int,
    column: int,
) -> tuple[int, int]:
    """Advance a 1-based line and column across one source interval."""
    newlines = source.count("\n", start, end)
    if newlines == 0:
        return line, column + end - start
    return line + newlines, end - source.rfind("\n", start, end)


def positioned_forms(source: str) -> list[SourceForm]:
    """Every top-level form with its exact source position.

    The engine's reader supplies kinds and verbatim texts; the walk here
    only skips inter-form whitespace and comments and then EXPECTS the
    next text in place, so a comment that quotes a later form can never
    mislead it, and any disagreement with the reader refuses loudly.
    """
    row = runtime().must("metta_py_read_forms(Source, Forms)", Source=source)
    forms: list[SourceForm] = []
    cursor = 0
    line = 1
    column = 1
    for kind, text in row["Forms"]:
        previous = cursor
        cursor = _skip_between(source, cursor)
        line, column = _advance_position(source, previous, cursor, line, column)
        if kind == "runnable":
            if cursor >= len(source) or source[cursor] != "!":
                msg = (
                    f"the position walk expected ! before a runnable form at "
                    f"offset {cursor}; the reader and the locator disagree"
                )
                raise MettaError(
                    msg
                )
            previous = cursor
            cursor = _skip_between(source, cursor + 1)
            line, column = _advance_position(
                source, previous, cursor, line, column
            )
        if not source.startswith(text, cursor):
            msg = (
                f"the position walk expected the form {text[:40]!r} at offset "
                f"{cursor}; the reader and the locator disagree"
            )
            raise MettaError(
                msg
            )
        forms.append(SourceForm(str(kind), str(text), line, column))
        end = cursor + len(text)
        line, column = _advance_position(source, cursor, end, line, column)
        cursor = end
    return forms
