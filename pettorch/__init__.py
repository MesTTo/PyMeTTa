"""Purpose: pettorch, PyTorch integrated with PeTTa as one instantiation of
the general interface: petta.arrays carries the whole tensor operation set
with torch as the constructor default, petta.integrate carries losses,
optimizers, wrapping and reflection, and what remains genuinely torch is
autograd, gelu and the nn.Module packaging of a MeTTa forward pass. The
package is the existence proof that the general system loses nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None

    import petta, pettorch

    m = petta.MeTTa()
    pettorch.install(m)
    m.run("!(t-tolist (matmul (tensor ((1.0 2.0))) (tensor ((3.0) (4.0)))))")
    # [[Expr('((11.0))')]]

Importing pettorch is free; torch loads on first use.
"""

from __future__ import annotations

from petta.arrays import EmbeddingStore

from . import reflect as _reflect_module
from .modules import MettaModule, wrap
from .neural import neural_predicate
from .reflect import VOCABULARY, reflect
from .tensors import TENSOR_OPS, install_tensor_ops
from .train import LOSS_OPS, attach_optimizer, install_loss_ops, train_step

__version__ = "0.2.0"

__all__ = [
    "install",
    "installed",
    "install_petta",
    "wrap",
    "MettaModule",
    "neural_predicate",
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
    """Register the whole torch integration on the shared engine.

    Idempotent per process, because operations are process-wide the way
    every MeTTa function is. Returns the registered names.
    """
    global _INSTALLED
    names = install_tensor_ops(m) + install_loss_ops(m)
    _reflect_module.register()
    _INSTALLED = True
    return names


#: The integration protocol's spelling, so m.integrate(pettorch) works.
install_petta = install


def installed() -> bool:
    return _INSTALLED
