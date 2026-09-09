"""Purpose: source positions for the engine's own reader, and the door a head
answers them through. The reader answers each form's KIND and verbatim TEXT
(metta_py_read_forms); between forms the grammar allows only whitespace and
;-comments, so a single deterministic walk recovers every form's line and
column exactly, with no search and no engine change: the consumers that want
positions pay here, and the hot compile path pays nothing, SWI's own
subterm_positions philosophy.
Assumes:
  - form texts are verbatim slices of the source in source order, and a
    runnable form's text excludes its leading ! [tested
    test_positioned_forms_recover_exact_lines]
  - metta_py_origin/3 answers [file, line, form index] per compiled clause,
    indexing the same parsed-form list metta_py_read_forms/2 answers, so the
    walk below is what turns an index into a line
    [source: extensions/python/metta/_binding/positions.pl:36 metta_py_origin/3;
    commit=WORKTREE]
Guarantees:
  - a locator/reader disagreement raises instead of guessing [tested
    test_a_locator_mismatch_refuses]
  - line and column tracking scans disjoint source intervals, so F forms in N
    characters take theta(N), not theta(N*F) [tested:
    test_position_tracking_scans_only_disjoint_source_intervals;
    commit=aa02d6c674b1e86eec5ddf32d111400df8f9e4b4]
  - head_origins answers one entry per compiled clause in clause order, and a
    source that no longer carries the equation loses the line rather than
    answering a wrong one [tested:
    test_every_clause_of_a_multi_clause_head_answers_in_clause_order,
    test_an_edited_file_loses_the_line_and_keeps_the_file; commit=6375a7c8f3c035b04bc9d41c8f7f22e56b42fb41]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import gzip
import pathlib
from typing import TYPE_CHECKING, NamedTuple

from metta._binding.runtime import runtime
from metta._errors.errors import MettaError


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


class Origin(NamedTuple):
    """Where one clause of a head was written.

    ``file`` is the source the engine read; ``line`` is its 1-based line
    when the engine can name one and None when it cannot. A clause with no
    source at all is not an Origin: ``head.origin`` answers None in that
    position.
    """

    file: str
    line: int | None


def _source_text(path: str) -> str:
    """The source the engine read, decompressing a .gz load the way it does."""
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return handle.read()
    return pathlib.Path(path).read_text(encoding="utf-8")


def _form_line(path: str, index: int, cache: dict[str, list[SourceForm]]) -> int | None:
    """The 1-based line of one top-level form of a source, or None.

    The engine answers WHICH form defines a clause and this answers WHERE
    that form sits, because _source_forms.positioned_forms walks the same
    parsed-form list the engine indexed, from the same reader. A source that
    has since been deleted, or edited past the form the clause came from,
    loses its line and keeps its file rather than answering a wrong number.
    """
    if index < 0:
        return None
    forms = cache.get(path)
    if forms is None:
        try:
            forms = positioned_forms(_source_text(path))
        except (OSError, MettaError):
            forms = []
        cache[path] = forms
    return forms[index].line if index < len(forms) else None


def head_origins(space: _root.Space, name: str) -> tuple[Origin | None, ...]:
    """One entry per compiled clause of a head, in clause order."""
    rows = space._rt.apply_must("metta_py_origin", space.name, name)
    cache: dict[str, list[SourceForm]] = {}
    origins: list[Origin | None] = []
    for path, line, index in rows:
        if not path:
            origins.append(None)
        elif line >= 0:
            origins.append(Origin(str(path), int(line)))
        else:
            origins.append(Origin(str(path), _form_line(str(path), int(index), cache)))
    return tuple(origins)

# Resolve annotations after definitions so peer imports can finish.
from metta._lazy import lazy  # noqa: E402 -- deferred annotation bindings

if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
