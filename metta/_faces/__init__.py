"""Purpose: expose common space operations through generated receiver classes."""

from metta._lazy import package as _package

__getattr__, __dir__ = _package(__name__)
