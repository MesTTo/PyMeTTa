"""Purpose: translate and schedule calls across the Python and Prolog boundary."""

from metta._lazy import package as _package

__getattr__, __dir__ = _package(__name__)
