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

from ._lint_analysis import analyze
from ._lint_model import EngineRegistry, Finding
from .foreign import require_capability

__all__ = ["Finding", "lint"]

Finding.__module__ = __name__


def lint(space) -> list[Finding]:
    """Diagnose a space and return an empty list when no check fires."""
    require_capability(space.space_name, "enumerate", "lint")
    return analyze(space, space.atoms(), EngineRegistry(space.runtime))
