"""Purpose: source positions for the engine's own reader. The reader
answers each form's KIND and verbatim TEXT (petta_py_read_forms); between
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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import NamedTuple

from ._engine import runtime
from .errors import PettaError


class SourceForm(NamedTuple):
    """One top-level form: the parser's kind, its verbatim text, and the
    1-based line and column its first character sits at.
    """

    kind: str
    text: str
    line: int
    column: int


def _skip_between(source: str, cursor: int) -> int:
    """Advance past what the grammar allows between forms: whitespace and
    ;-comments to end of line.
    """
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


def positioned_forms(source: str) -> list[SourceForm]:
    """Every top-level form with its exact source position.

    The engine's reader supplies kinds and verbatim texts; the walk here
    only skips inter-form whitespace and comments and then EXPECTS the
    next text in place, so a comment that quotes a later form can never
    mislead it, and any disagreement with the reader refuses loudly.
    """
    row = runtime().must("petta_py_read_forms(Source, Forms)", Source=source)
    forms: list[SourceForm] = []
    cursor = 0
    for kind, text in row["Forms"]:
        cursor = _skip_between(source, cursor)
        if kind == "runnable":
            if cursor >= len(source) or source[cursor] != "!":
                msg = (
                    f"the position walk expected ! before a runnable form at "
                    f"offset {cursor}; the reader and the locator disagree"
                )
                raise PettaError(
                    msg
                )
            cursor = _skip_between(source, cursor + 1)
        if not source.startswith(text, cursor):
            msg = (
                f"the position walk expected the form {text[:40]!r} at offset "
                f"{cursor}; the reader and the locator disagree"
            )
            raise PettaError(
                msg
            )
        line = 1 + source.count("\n", 0, cursor)
        column = cursor - source.rfind("\n", 0, cursor)
        forms.append(SourceForm(str(kind), str(text), line, column))
        cursor += len(text)
    return forms
