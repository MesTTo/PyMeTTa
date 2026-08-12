"""Purpose: the tensor operations pettorch installs. The whole array set is
petta.arrays, the library-agnostic layer over the array API standard, with
torch as the constructor default; what remains here is only what genuinely
is torch and not arrays: autograd controls and gelu. That split is the
proof the general system carries the integration whole.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from petta import arrays
from petta.arrays import EmbeddingStore  # noqa: F401  compat re-export

from ._torch import torch

__all__ = ["install_tensor_ops", "TENSOR_OPS", "atom_to_data"]

TENSOR_OPS: list[str] = []

# Compat alias: tensor data conversion lives in the general layer now.
atom_to_data = arrays.data_of


def install_tensor_ops(m) -> list[str]:
    """The generic array set with torch constructing, plus torch's autograd."""
    t = torch()
    registered = list(arrays.install(m, default=t))

    def op(fn, *, name: str, **kw):
        m.op(fn, name=name, raw=True, typed=False, **kw)
        registered.append(name)

    # Autograd is torch's own capability, registered through the same public
    # interface any integration uses; nothing engine-side knows torch exists.
    op(lambda a: a.requires_grad_(True), name="t-requires-grad!")
    op(lambda a: a.detach(), name="t-detach")

    def backward(a) -> bool:
        a.backward()
        return True

    op(backward, name="t-backward!")

    def grad(a):
        return a.grad if a.grad is not None else None  # semidet: no grad yet

    op(grad, name="t-grad")

    op(lambda a: t.nn.functional.gelu(a), name="gelu")
    op(lambda a, target: a.to(target), name="t-to")

    TENSOR_OPS[:] = registered
    return registered
