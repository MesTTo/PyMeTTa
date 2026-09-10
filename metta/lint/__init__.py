"""Purpose: diagnose declarations, equations and calls, and apply the repairs.

Guarantees:
  - public Finding records retain the metta.lint pickle identity [tested:
    test_finding_retains_public_pickle_identity; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a lint invocation records and applies exact ``# metta: ok(kind)`` source
    intents without changing the space or executing findings [tested:
    test_a_named_metta_ok_intent_suppresses_only_its_bound_rule; commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - every finding lint_file answers carries the file it came from and the
    sha256 of the bytes that were read, so a repair can refuse a file that
    moved under it [tested: test_fix_refuses_a_file_that_changed_since_lint_read_it;
    commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
  - apply() and fix_file() apply only "machine" remedies and answer every
    finding they did not apply with the reason [tested:
    test_apply_repairs_a_space_and_names_what_it_left,
    test_fix_removes_a_duplicate_equation_and_relints_clean; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
  - diagnostics() answers LSP 3.17 Diagnostic objects with zero-based
    positions and the remedy under data [tested:
    test_lint_json_prints_one_lsp_diagnostic_per_line; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import pathlib
from dataclasses import dataclass
from typing import Any

import metta._faces.space as _space_face
from metta._atoms.designation import SpaceLike
from metta._atoms.factories import Atom, Variable, _alpha, _alpha_eq, _encode, _map_atoms, parse
from metta._binding.positions import positioned_forms
from metta._catalog.meaning import EngineRegistry
from metta._errors.errors import Remedy
from metta._spaces.intents import prepare_lint
from metta.foreign import require_capability
from metta.lint._analysis import analyze
from metta.lint._model import Finding

__all__ = [
    "Finding",
    "Repair",
    "Skipped",
    "apply",
    "diagnostics",
    "fix_file",
    "lint",
    "lint_file",
]

Finding.__module__ = __name__

#: Only this level is applied without being asked, which is what
#: `cargo fix` does with rustc's MachineApplicable and clang-tidy does with
#: its fix-it hints: a repair that MAY be wrong is shown, never written.
_APPLIED = "machine"


@dataclass(frozen=True)
class Skipped:
    """One finding a repair pass did not apply, and why."""

    finding: Finding
    reason: str

    def __str__(self) -> str:
        """The finding, then the one line saying why it stayed."""
        return f"{self.finding}\n    not applied: {self.reason}"


@dataclass(frozen=True)
class Repair:
    """What one repair pass did to one target.

    `applied` are the findings whose remedy was written, `skipped` the rest
    with their reasons, and `refused` is the one condition that stops the
    whole target rather than one finding: a file whose bytes changed since
    lint read them. `written` says whether anything reached the disk.
    """

    target: str
    applied: tuple[Finding, ...] = ()
    skipped: tuple[Skipped, ...] = ()
    written: bool = False
    refused: str | None = None

    @property
    def remaining(self) -> int:
        """How many findings this pass left standing."""
        return len(self.skipped)


def lint(space: SpaceLike) -> list[Finding]:
    """Diagnose a space and return an empty list when no check fires.

    One of nine observability methods, the one for the silently-wrong
    class; rows.why() explains one empty answer, and the guide's
    observability page maps the family. space may be a context or a space.
    """
    home = space.self
    require_capability(home.name, "enumerate", "lint")
    invocation = prepare_lint(home)
    return analyze(
        home,
        home.atoms(),
        EngineRegistry(home.runtime),
        invocation,
    )


def lint_file(
    path: str | os.PathLike[str], *, m: SpaceLike | None = None
) -> list[Finding]:
    """Diagnose one source file, each finding anchored to its line.

    The file loads into a scratch space and lint() runs there; every
    finding whose atom alpha-matches a top-level form then carries
    {"file", "line", "column"} in its payload, recovered exactly from
    the reader's own verbatim form texts, so a tool prints path:line
    without the engine ever tracking positions on its hot path. A
    finding about an atom no single form wrote, or one a form computed,
    stays unanchored rather than guessed. m may be a context or a space.

    Every finding also carries "digest", the sha256 of the bytes read
    here, which is what fix_file() compares against before writing.
    """
    source = os.fspath(path)
    text = pathlib.Path(source).read_text(encoding="utf-8")
    digest = _digest(text)
    anchors = [
        (parse(form.text), form.line, form.column)
        for form in positioned_forms(text)
        if form.kind != "runnable"
    ]
    engine = (
        _space_face.Space()
        if m is None
        else m.self
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
        extra: dict[str, Any] = {"file": source, "digest": digest}
        if position is not None:
            extra["line"], extra["column"] = position
        payload = {**finding.payload, **extra} if finding.payload else extra
        anchored.append(dataclasses.replace(finding, payload=payload))
    return anchored


def apply(space, findings: list[Finding] | None = None) -> Repair:
    """Write every machine remedy of FINDINGS into SPACE, and say what it left.

    A space is a multiset, so the two acts are exactly remove and add: a
    `replace` remedy removes the stored atom and adds its replacement, a
    removal remedy removes it and adds nothing, and an `edit` remedy adds
    the atom it names. Its longhand is that pair of calls per finding:

        m.remove(finding.atom)
        m.add(finding.remedy.replace[1])

    findings defaults to lint(space), so `apply(m)` is diagnose-and-repair.
    Only "machine" remedies are written; everything else comes back in
    `skipped` with its reason, which is what `cargo fix` does with rustc's
    non-MachineApplicable suggestions.
    """
    target = space.self
    found = lint(target) if findings is None else findings
    applied: list[Finding] = []
    skipped: list[Skipped] = []
    for finding in found:
        reason = _unapplicable(finding)
        if reason is not None:
            skipped.append(Skipped(finding, reason))
            continue
        remedy = finding.remedy
        # _unapplicable answered None, so the remedy is present and applicable.
        assert remedy is not None  # nosec B101 # _unapplicable already established an actionable remedy
        if remedy.replace is not None:
            stored, replacement = remedy.replace
            if not target.remove(stored):
                skipped.append(Skipped(finding, "the atom is no longer stored"))
                continue
            if replacement is not None:
                target.add(replacement)
        if remedy.edit is not None:
            target.add(remedy.edit)
        applied.append(finding)
    return Repair(str(target.name), tuple(applied), tuple(skipped), written=bool(applied))


def fix_file(
    path: str | os.PathLike[str],
    findings: list[Finding] | None = None,
    *,
    m=None,
) -> Repair:
    """Rewrite one source file with the machine remedies its findings carry.

    A file finding is applied only where its line still holds exactly the
    form the finding stands on, so a stale anchor writes nothing. Edits are
    spliced from the end of the file backwards, which is how a fix-it
    applier keeps earlier offsets valid, and two repairs over one form leave
    the second unapplied rather than writing over each other.

    The whole file is refused, with nothing written, when its bytes differ
    from the ones lint_file() read; the digest travels in each finding's
    payload and is this library's document version. LSP writes the same
    guard as OptionalVersionedTextDocumentIdentifier, whose version is the
    one the edit was computed against, and a held-then-stale diagnostic is
    exactly the case findings= drives [source: LSP 3.17 TextDocumentEdit,
    https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocumentEdit;
    commit=3fc5479961fd591b1884af118528c9a64a1afbb7].

    findings defaults to lint_file(path, m=m), so `fix_file(path)` is
    diagnose-and-repair; its longhand is that call plus the splice, which
    `python -m metta lint --fix` runs.
    """
    source = os.fspath(path)
    if findings is None:
        findings = lint_file(source, m=m)
    text = pathlib.Path(source).read_text(encoding="utf-8")
    recorded = next(
        ((finding.payload or {}).get("digest") for finding in findings), None
    )
    if recorded is not None and recorded != _digest(text):
        return Repair(
            source,
            skipped=tuple(
                Skipped(finding, "the file changed since lint read it")
                for finding in findings
            ),
            refused="the file changed since lint read it",
        )
    forms = {
        (form.line, form.column): form
        for form in positioned_forms(text)
        if form.kind != "runnable"
    }
    starts = _line_starts(text)
    edits: list[tuple[int, int, str, Finding]] = []
    skipped: list[Skipped] = []
    for finding in findings:
        reason = _unapplicable(finding)
        if reason is not None:
            skipped.append(Skipped(finding, reason))
            continue
        payload = finding.payload or {}
        line, column = payload.get("line"), payload.get("column")
        if not isinstance(line, int) or not isinstance(column, int):
            skipped.append(Skipped(finding, "the finding is not anchored to a line"))
            continue
        form = forms.get((line, column))
        if form is None:
            skipped.append(Skipped(finding, "the line no longer holds a form"))
            continue
        renaming: dict[str, str] = {}
        if not _alpha(_encode(finding.atom), _encode(parse(form.text)), renaming, {}):
            skipped.append(
                Skipped(finding, "the line no longer holds exactly this form")
            )
            continue
        start = starts[line - 1] + column - 1
        edits.append(
            (start, start + len(form.text), _rewritten(finding, renaming), finding)
        )
    applied: list[Finding] = []
    covered: set[int] = set()
    for start, end, replacement, finding in sorted(edits, key=_edit_order, reverse=True):
        if start in covered:
            skipped.append(
                Skipped(finding, "another repair already rewrote this form")
            )
            continue
        covered.add(start)
        text = _spliced(text, start, end, replacement)
        applied.append(finding)
    if applied:
        pathlib.Path(source).write_text(text, encoding="utf-8")
    return Repair(
        source, tuple(reversed(applied)), tuple(skipped), written=bool(applied)
    )


def diagnostics(findings: list[Finding]) -> list[dict[str, Any]]:
    """Every finding as one LSP 3.17 Diagnostic object.

    `range` is zero-based, which is LSP's own convention against the
    1-based line a finding carries, and covers the whole line when only the
    line is known; `code` is the finding kind, `source` is "metta", and
    `data` carries the remedy and the docs link, which LSP preserves between
    publishDiagnostics and textDocument/codeAction so a client turns the
    remedy into a CodeAction without asking the server again [source: LSP
    3.17 Diagnostic.data,
    https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#diagnostic;
    commit=3fc5479961fd591b1884af118528c9a64a1afbb7].

    Its longhand is reading the fields off each Finding.
    """
    lines: dict[str, list[str]] = {}
    return [_diagnostic(finding, lines) for finding in findings]


def _digest(text: str) -> str:
    """The sha256 of one source, which is what a repair compares."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_starts(text: str) -> list[int]:
    """The absolute offset each 1-based line begins at."""
    starts = [0]
    for index, character in enumerate(text):
        if character == "\n":
            starts.append(index + 1)
    return starts


def _unapplicable(finding: Finding) -> str | None:
    """Why this finding cannot be written, or None when it can."""
    remedy = finding.remedy
    if remedy is None:
        return "the finding carries no remedy"
    if remedy.applicability != _APPLIED:
        return f"the remedy is {remedy.applicability}, not {_APPLIED}"
    if remedy.replace is remedy.edit is None:
        return "the remedy is host text rather than an edit"
    return None


def _edit_order(edit: tuple[int, int, str, Finding]) -> tuple[int, int]:
    """Order edits by their span, so the sort never compares two findings."""
    return edit[0], edit[1]


def _rewritten(finding: Finding, renaming: dict[str, str]) -> str:
    """The source text one machine remedy leaves in place of its form.

    A finding stands on the atom the ENGINE stored, whose variables carry
    the engine's own names, so writing the replacement back verbatim would
    rename every variable in the author's line. RENAMING is the substitution
    the alpha check already computed between the two, so what lands is the
    same rewrite spelled the way the source spells it, which is what a
    compiler fix-it does by splicing source text rather than a printed tree.
    """
    remedy = finding.remedy
    # Only a finding _unapplicable cleared reaches here.
    assert remedy is not None  # nosec B101 # _unapplicable already established an actionable remedy
    parts: list[Atom] = []
    if remedy.replace is not None and remedy.replace[1] is not None:
        parts.append(remedy.replace[1])
    if remedy.edit is not None:
        parts.append(remedy.edit)
    return "\n".join(str(_renamed(part, renaming)) for part in parts)


def _renamed(atom: Atom, renaming: dict[str, str]) -> Atom:
    """One atom with the engine's variable names put back to the source's."""
    if not renaming:
        return atom
    return _map_atoms(
        atom,
        lambda node: (
            Variable(renaming[node.name])
            if isinstance(node, Variable) and node.name in renaming
            else node
        ),
    )


def _spliced(text: str, start: int, end: int, replacement: str) -> str:
    """TEXT with one span replaced, dropping a line the removal empties.

    A removal that leaves only whitespace between two newlines takes the
    whole line with it, which is what deleting a statement means in every
    editor; a removal with other text beside it leaves that text alone.
    """
    if replacement:
        return text[:start] + replacement + text[end:]
    opening = text.rfind("\n", 0, start) + 1
    closing = text.find("\n", end)
    closing = len(text) if closing < 0 else closing + 1
    if not text[opening:start].strip() and not text[end : closing - 1].strip():
        return text[:opening] + text[closing:]
    return text[:start] + text[end:]


def _diagnostic(finding: Finding, lines: dict[str, list[str]]) -> dict[str, Any]:
    """One finding as an LSP Diagnostic, reading source lines once per file."""
    payload = finding.payload or {}
    line, path = payload.get("line"), payload.get("file")
    start = 0 if line is None else line - 1
    end = 0
    if line is not None and isinstance(path, str):
        if path not in lines:
            lines[path] = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        source = lines[path]
        end = len(source[line - 1]) if line <= len(source) else 0
    data: dict[str, Any] = {"docs": finding.docs_link}
    if finding.remedy is not None:
        data["remedy"] = _remedy_json(finding.remedy)
    return {
        "range": {
            "start": {"line": start, "character": 0},
            "end": {"line": start, "character": end},
        },
        "severity": finding.lsp_severity,
        "code": finding.kind,
        "source": "metta",
        "message": finding.message,
        "data": data,
    }


def _remedy_json(remedy: Remedy) -> dict[str, Any]:
    """One remedy as the JSON an editor reads, atoms rendered as their text.

    The same four acts `Remedy.as_atom` writes, under the same names, so a
    client that has the atom and a client that has the JSON are reading one
    vocabulary; an act the remedy does not carry is absent rather than null.
    """
    encoded: dict[str, Any] = {
        "title": remedy.title,
        "kind": remedy.kind,
        "applicability": remedy.applicability,
    }
    if remedy.edit is not None:
        encoded["edit"] = str(remedy.edit)
    if remedy.replace is not None:
        stored, replacement = remedy.replace
        if replacement is None:
            encoded["remove"] = str(stored)
        else:
            encoded["replace"] = [str(stored), str(replacement)]
    if remedy.python is not None:
        encoded["python"] = remedy.python
    return encoded
