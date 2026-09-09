"""Purpose: lower Python syntax into MeTTa equations."""

from metta._lazy import package as _package

__getattr__, __dir__ = _package(__name__)
