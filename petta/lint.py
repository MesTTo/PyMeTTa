"""Purpose: expose diagnostics for declarations, equations, and calls.
Guarantees:
  - lint() refuses spaces that cannot enumerate their contents [tested
    test_das_space_refuses_unsupported_composed_operations_at_entry]
  - public Finding records retain the petta.lint pickle identity [tested
    test_finding_retains_public_pickle_identity]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import os
import pathlib

from ._lint_analysis import analyze
from ._lint_model import EngineRegistry, Finding
from ._source_forms import positioned_forms
from .atoms import alpha_eq, parse
from .foreign import require_capability

__all__ = ["Finding", "lint", "lint_file"]

Finding.__module__ = __name__


def lint(space) -> list[Finding]:
    """Diagnose a space and return an empty list when no check fires.

    One of nine observability doors, the one for the silently-wrong
    class; rows.why() explains one empty answer, and the guide's
    observability page maps the family."""
    require_capability(space.space_name, "enumerate", "lint")
    return analyze(space, space.atoms(), EngineRegistry(space.runtime))


def lint_file(path: str | os.PathLike[str], *, m=None) -> list[Finding]:
    """Diagnose one source file, each finding anchored to its line.

    The file loads into a scratch space and lint() runs there; every
    finding whose atom alpha-matches a top-level form then carries
    {"file", "line", "column"} in its payload, recovered exactly from
    the reader's own verbatim form texts, so a tool prints path:line
    without the engine ever tracking positions on its hot path. A
    finding about an atom no single form wrote, or one a form computed,
    stays unanchored rather than guessed.
    """
    from .space import MeTTa  # noqa: PLC0415  space.py imports lint at top; the cycle breaks here

    source = os.fspath(path)
    text = pathlib.Path(source).read_text(encoding="utf-8")
    anchors = [
        (parse(form.text), form.line, form.column)
        for form in positioned_forms(text)
        if form.kind != "runnable"
    ]
    engine = MeTTa() if m is None else m
    with engine.new_space() as scratch:
        scratch.load(source)
        found = lint(scratch)
    anchored = []
    for finding in found:
        position = next(
            (
                (line, column)
                for atom, line, column in anchors
                if alpha_eq(atom, finding.atom)
            ),
            None,
        )
        if position is None:
            anchored.append(finding)
            continue
        line, column = position
        extra = {"file": source, "line": line, "column": column}
        payload = {**finding.payload, **extra} if finding.payload else extra
        anchored.append(dataclasses.replace(finding, payload=payload))
    return anchored
