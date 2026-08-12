"""Purpose: the single lazy gateway to torch. Everything in pettorch imports
torch through here, so a missing installation surfaces once, with the fix in
the message, and importing pettorch itself stays free. Printing and typing
of tensors need nothing here: the DLPack protocol registrations in
petta.arrays cover every array library at once.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

_TORCH = None


def torch():
    """The torch module, imported on first use.

    Raises ImportError with the install command when torch is absent, which
    is the one deferral this package allows itself: PyTorch is the user's
    dependency to choose a build of (CPU, CUDA, ROCm), not this package's to
    pick for them.
    """
    global _TORCH
    if _TORCH is None:
        try:
            import torch as t
        except ImportError as exc:
            raise ImportError(
                "pettorch needs PyTorch, which is not installed. Install a "
                "build matching your hardware, for example: pip install torch"
            ) from exc
        _TORCH = t
    return _TORCH
