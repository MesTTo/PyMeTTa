"""Purpose: register program definitions, operations and declaration contracts."""

from metta._lazy import package as _package

__getattr__, __dir__ = _package(__name__)
