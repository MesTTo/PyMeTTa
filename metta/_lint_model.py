"""Purpose: represent one lint finding. The engine facts a finding is drawn
from live in _head_meaning.py, which why() reads too.
Guarantees:
  - a finding renders its kind, subject, detail, suggestion and autofix in one
    line [tested: test_findings_carry_the_lsp_diagnostic_fields;
    commit=bd3a1bbad63952fc7c0d7367f38237dd1c219d8b]
  - a finding carrying a remedy renders that remedy's title in place of the
    bare autofix atom, still on one line, and its severity maps to LSP's own
    1..4 [tested: test_a_finding_renders_its_remedy_in_place_of_the_atom,
    test_lint_json_prints_one_lsp_diagnostic_per_line; commit=3fc5479961fd591b1884af118528c9a64a1afbb7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .atoms import Atom
from .errors import Remedy

#: The guide's lint section is the catalogue: every kind, what it means and
#: which severity it carries. One link serves the whole family rather than
#: one per kind, because a reader who has one finding usually wants the
#: neighbouring kinds too. NOT the generated reference page, which
#: reproduces signatures and docstrings and names no kind at all.
_LINT_DOCS = (
    "https://github.com/MesTTo/MeTTa-Kernel/blob/main/website/guide/run-query.md"
    "#lint-a-space"
)

#: LSP DiagnosticSeverity, which is an integer on the wire: Error 1, Warning 2,
#: Information 3, Hint 4 [source: LSP 3.17 DiagnosticSeverity,
#: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#diagnostic;
#: commit=3fc5479961fd591b1884af118528c9a64a1afbb7].
LSP_SEVERITY = {"error": 1, "warning": 2, "information": 3, "hint": 4}


@dataclass(frozen=True)
class Finding:
    """One diagnostic in the LSP's own vocabulary: what and where in the
    first four fields, and how much, what instead, where to read, the
    structured parts, the machine-applicable edit and the repair in the
    next six.

    severity is LSP's: "error" (the program is wrong), "warning" (almost
    certainly not what was meant), "information" (true and worth knowing),
    "hint" (a heuristic). autofix, when present, is an ATOM: the stored
    atom rewritten with the simplification applied, so applying the fix
    is remove(finding.atom) then add(finding.autofix), no source
    positions needed.

    remedy generalises autofix: it says WHAT KIND of repair this is and how
    far it can be trusted, and it covers the repairs autofix has no shape
    for, a removal and a near-miss rename among them. Every finding that
    carries an autofix carries the same rewrite again as
    `remedy.replace`, so a reader may take either.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    kind: str
    subject: str
    detail: str
    atom: Atom
    severity: str = "warning"
    suggestion: str | None = None
    docs_link: str = _LINT_DOCS
    payload: Mapping[str, Any] | None = None
    autofix: Atom | None = None
    remedy: Remedy | None = None

    @property
    def message(self) -> str:
        """The sentence without the kind, which is what LSP wants.

        A Diagnostic carries the kind in `code` rather than repeating it in
        `message`. Its longhand is `str(finding)`, this line behind the kind.
        """
        rendered = f"{self.subject}: {self.detail}"
        if self.suggestion is not None:
            rendered += f" (did you mean {self.suggestion}?)"
        if self.remedy is not None:
            rendered += f" (fix: {self.remedy.title})"
        elif self.autofix is not None:
            rendered += f" (fix: {self.autofix})"
        return rendered

    @property
    def lsp_severity(self) -> int:
        """This finding's severity as LSP's integer, 1 through 4."""
        return LSP_SEVERITY[self.severity]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message}"
