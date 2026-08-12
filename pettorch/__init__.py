"""Purpose: pettorch, the deep integration between PeTTa's MeTTa and PyTorch.
Both directions and the structure itself: tensors are atoms with identity, an
nn.Module is a MeTTa function, a MeTTa program is an nn.Module, architectures
reflect into facts rules can match, training runs through the engine with the
autograd graph intact, and similarity search is a nondeterministic operation.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None

    import petta, pettorch

    m = petta.MeTTa()
    pettorch.install(m)
    m.run("!(t-tolist (matmul (tensor ((1.0 2.0))) (tensor ((3.0) (4.0)))))")
    # [[Expr('((11.0))')]]

Importing pettorch is free; torch loads on first use and a missing torch
raises with the install command.
"""

from __future__ import annotations

from .knn import EmbeddingStore
from .modules import MettaModule, wrap
from .reflect import VOCABULARY, reflect
from .tensors import TENSOR_OPS, install_tensor_ops
from .train import LOSS_OPS, attach_optimizer, install_loss_ops, train_step

__version__ = "0.2.0"

__all__ = [
    "install",
    "installed",
    "wrap",
    "MettaModule",
    "reflect",
    "VOCABULARY",
    "EmbeddingStore",
    "attach_optimizer",
    "train_step",
    "install_tensor_ops",
    "install_loss_ops",
    "TENSOR_OPS",
    "LOSS_OPS",
    "__version__",
]

_INSTALLED = False


def install(m) -> list[str]:
    """Register the whole operation set on the shared engine.

    Idempotent per process, because operations are process-wide the way every
    MeTTa function is: installing through one space serves them all. Returns
    the registered names.
    """
    global _INSTALLED
    names = install_tensor_ops(m) + install_loss_ops(m)
    _INSTALLED = True
    return names


def installed() -> bool:
    return _INSTALLED
