"""Purpose: construct reader-token atoms for the engine's Python host seam.
Guarantees:
  - a constructor receives the complete matched lexeme and may return either
    an Atom or any value accepted by encode; both cross as the same Atom wire
    [tested: test_a_registered_token_class_parses_like_a_shipped_one;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from collections.abc import Callable
from typing import Any

from .atoms import Atom, encode


def construct_token(constructor: Callable[[str], Any], token: str) -> list:
    """Invoke one retained reader constructor and return its Atom wire."""
    value = constructor(token)
    atom = value if isinstance(value, Atom) else encode(value)
    return atom.to_wire()
