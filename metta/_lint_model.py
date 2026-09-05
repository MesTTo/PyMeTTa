"""Purpose: represent one lint finding. The engine facts a finding is drawn
from live in _head_meaning.py, which why() reads too.
Guarantees:
  - a finding renders its kind, subject, detail, suggestion and autofix in one
    line [tested: test_findings_carry_the_lsp_diagnostic_fields;
    commit=WORKTREE]
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

#: The guide's lint section is the catalogue: every kind, what it means and
#: which severity it carries. One link serves the whole family rather than
#: one per kind, because a reader who has one finding usually wants the
#: neighbouring kinds too. NOT the generated reference page, which
#: reproduces signatures and docstrings and names no kind at all.
_LINT_DOCS = (
    "https://github.com/MesTTo/MeTTa-Kernel/blob/main/website/guide/run-query.md"
    "#lint-a-space"
)


@dataclass(frozen=True)
class Finding:
    """One diagnostic in the LSP's own vocabulary: what and where in the
    first four fields, and how much, what instead, where to read, the
    structured parts, and the machine-applicable edit in the next five.

    severity is LSP's: "error" (the program is wrong), "warning" (almost
    certainly not what was meant), "information" (true and worth knowing),
    "hint" (a heuristic). autofix, when present, is an ATOM: the stored
    atom rewritten with the simplification applied, so applying the fix
    is remove(finding.atom) then add(finding.autofix), no source
    positions needed.
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

    def __str__(self) -> str:
        rendered = f"[{self.kind}] {self.subject}: {self.detail}"
        if self.suggestion is not None:
            rendered += f" (did you mean {self.suggestion}?)"
        if self.autofix is not None:
            rendered += f" (fix: {self.autofix})"
        return rendered
