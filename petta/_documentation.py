"""Purpose: turn Python callable documentation into the portable MeTTa
``(@doc name (@desc ...))`` atom used by operation and definition lifecycles.
Guarantees:
  - inspect.getdoc supplies one cleaned description, or no atom when the
    source has no documentation [tested:
    test_every_register_op_writes_its_declaration_and_get_doc_answers;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

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
