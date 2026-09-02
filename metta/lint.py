"""Purpose: expose diagnostics for declarations, equations, and calls.
Guarantees:
  - public Finding records retain the metta.lint pickle identity [tested:
    test_finding_retains_public_pickle_identity; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a lint invocation records and applies exact ``# metta: ok(kind)`` source
    intents without changing the space or executing findings [tested:
    test_a_named_metta_ok_intent_suppresses_only_its_bound_rule; commit=acb40f1912f131ae088083d1af29b4b283019bea]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import dataclasses
import importlib as _importlib
import os
import pathlib

from ._lint_analysis import analyze
from ._lint_events import prepare_lint
from ._lint_model import EngineRegistry, Finding
from ._source_forms import positioned_forms
from .atoms import _alpha_eq, parse
from .foreign import require_capability

__all__ = ["Finding", "lint", "lint_file"]

Finding.__module__ = __name__


def lint(space) -> list[Finding]:
    """Diagnose a space and return an empty list when no check fires.

    One of nine observability methods, the one for the silently-wrong
    class; rows.why() explains one empty answer, and the guide's
    observability page maps the family.
    """
    require_capability(space.name, "enumerate", "lint")
    invocation = prepare_lint(space)
    return analyze(
        space,
        space.atoms(),
        EngineRegistry(space.runtime),
        invocation,
    )


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
    source = os.fspath(path)
    text = pathlib.Path(source).read_text(encoding="utf-8")
    anchors = [
        (parse(form.text), form.line, form.column)
        for form in positioned_forms(text)
        if form.kind != "runnable"
    ]
    engine = (
        _importlib.import_module(f"{__package__}._space").Space()
        if m is None
        else m
    )
    with engine._new_space() as scratch:
        scratch.load(source)
        found = lint(scratch)
    anchored = []
    for finding in found:
        position = next(
            (
                (line, column)
                for atom, line, column in anchors
                if _alpha_eq(atom, finding.atom)
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
