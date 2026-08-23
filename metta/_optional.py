"""Purpose: import optional integrations lazily with precise missing-package errors.
Guarantees:
  - a missing requested package gets the caller's install guidance, while an
    ImportError inside an installed package propagates unchanged [tested
    test_optional_import_preserves_broken_dependency_errors]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from importlib import import_module
from types import ModuleType


def optional_module(name: str) -> ModuleType | None:
    """Import a module, returning None only when that module itself is absent."""
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name not in (name, name.partition(".")[0]):
            raise
        return None


def require_module(name: str, message: str) -> ModuleType:
    """Import an optional module or raise the supplied installation guidance."""
    module = optional_module(name)
    if module is None:
        raise ImportError(message)
    return module
