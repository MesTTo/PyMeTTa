"""Purpose: own space handles, lifetimes, storage and answer consumption."""

from metta._lazy import package as _package

__getattr__, __dir__ = _package(__name__)
