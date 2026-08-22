"""Purpose: turn Python callable documentation into the portable MeTTa
``(@doc name (@desc ...) (@params ...) (@return ...))`` atom the operation and
definition lifecycles write, and that get-doc answers.
Assumes: a sectioned docstring is Google style, the style this repository and
  napoleon both write; anything else stays one description and loses nothing.
Guarantees:
  - inspect.getdoc supplies one cleaned description, or no atom when the
    source has no documentation [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers;
    commit=WORKTREE]
  - compiled definitions use the same portable atom and cleaned text [tested:
    test_one_docstring_reaches_help_dot_doc_and_get_doc;
    commit=WORKTREE]
  - an Args section becomes one (@param ...) per PARAMETER OF THE SIGNATURE, in
    signature order, and a Returns section becomes (@return ...), which is the
    engine's own shape [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=WORKTREE]
Fails when: a docstring documents a parameter the signature does not have. The
  signature decides the list and its order, so the stray entry is dropped
  rather than shifting every later parameter's description onto the wrong one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect
import re
from typing import Any

from .atoms import Expression, S, _expr

__all__ = ["documentation_atom"]

#: A Google-style section header, `Args:` or `Returns:` on its own line. The
#: names are napoleon's, so a docstring written for Sphinx reads here too
#: [source: sphinx.ext.napoleon, "Google style", the _sections table].
_SECTION = re.compile(
    r"^(Args|Arguments|Parameters|Returns|Return|Yields|Raises|Examples|Example|"
    r"Note|Notes|Attributes|Warns|Warnings|Todo|References|See Also)\s*:\s*$",
    re.MULTILINE,
)

#: One documented parameter inside an Args section: a name, an optional
#: parenthesised type, then a colon and the description. Continuation lines are
#: indented further and are joined onto it.
_PARAMETER = re.compile(r"^(\*{0,2}\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)$")

_ARGUMENT_SECTIONS = frozenset({"Args", "Arguments", "Parameters"})
_RETURN_SECTIONS = frozenset({"Returns", "Return", "Yields"})


def _sections(documentation: str) -> tuple[str, dict[str, str]]:
    """Split a cleaned docstring into its summary and its named sections."""
    matches = list(_SECTION.finditer(documentation))
    if not matches:
        return documentation, {}
    summary = documentation[: matches[0].start()].strip()
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(documentation)
        sections[match.group(1)] = documentation[match.end() : end].strip("\n")
    return summary, sections


def _documented_parameters(body: str) -> dict[str, str]:
    """Read an Args section into name-to-description pairs."""
    described: dict[str, str] = {}
    current: str | None = None
    for line in inspect.cleandoc(body).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _PARAMETER.match(stripped)
        if match is not None and not line.startswith((" ", "\t")):
            current = match.group(1).lstrip("*")
            described[current] = match.group(2).strip()
        elif current is not None:
            described[current] = f"{described[current]} {stripped}".strip()
    return described


def _parameter_names(source: object) -> list[str]:
    """The callable's own parameter names, in signature order."""
    if not callable(source):
        return []
    try:
        signature = inspect.signature(source)
    except (TypeError, ValueError):
        return []
    return [
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is not inspect.Parameter.VAR_KEYWORD and name != "self"
    ]


def _paragraph(text: str) -> str:
    """One section's text as a single line, the way the engine's own @doc reads."""
    return " ".join(inspect.cleandoc(text).split())


def documentation_atom(name: str, source: object) -> Expression | None:
    """Return the source's docstring as the engine's own @doc vocabulary."""
    documentation = inspect.getdoc(source)
    if not documentation:
        return None
    summary, sections = _sections(documentation)
    fields: list[Any] = [_expr(S["@desc"], summary or documentation)]

    described = {}
    for heading in _ARGUMENT_SECTIONS:
        if heading in sections:
            described = _documented_parameters(sections[heading])
            break
    if described:
        # The SIGNATURE decides the list and its order, because a @param is
        # positional in the engine's shape: the nth (@param ...) documents the
        # nth argument, so a docstring that names a parameter the function does
        # not take must not shift the rest.
        ordered = [
            _expr(S["@param"], described.get(parameter, ""))
            for parameter in _parameter_names(source)
        ]
        if ordered:
            fields.append(_expr(S["@params"], _expr(*ordered)))

    for heading in _RETURN_SECTIONS:
        if heading in sections:
            fields.append(_expr(S["@return"], _paragraph(sections[heading])))
            break

    return _expr(S["@doc"], S[name], *fields)
