"""Purpose: turn Python callable documentation into the portable MeTTa
``(@doc name (@desc ...))`` atom used by operation and definition lifecycles.
Guarantees:
  - inspect.getdoc supplies one cleaned description, or no atom when the
    source has no documentation [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers;
    commit=eda90565cfb66417c62e654b0f3e7b55351366c5]
  - compiled definitions use the same portable atom and cleaned text [tested:
    test_one_docstring_reaches_help_dot_doc_and_get_doc;
    commit=6b1c4595fd5228557b563b56a22cdd8635052a00]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import inspect

from .atoms import Expr, S, expr

__all__ = ["documentation_atom"]


def documentation_atom(name: str, source: object) -> Expr | None:
    """Return the source's cleaned docstring as ordinary MeTTa data."""
    documentation = inspect.getdoc(source)
    if not documentation:
        return None
    return expr(S["@doc"], S[name], expr(S["@desc"], documentation))
