"""Purpose: training as MeTTa, assembled from the general integration
toolkit: losses arrive through module_ops over torch.nn.functional, an
optimizer's step and zero_grad through wrap_object, and train_step runs one
whole update with the forward pass in MeTTa. Nothing here is machinery of
its own; that is the point.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from petta import S, expr
from petta.integrate import module_ops, wrap_object

from ._torch import torch

__all__ = ["install_loss_ops", "attach_optimizer", "train_step", "LOSS_OPS"]

LOSS_OPS: list[str] = []


def install_loss_ops(m) -> list[str]:
    """mse-loss, cross-entropy and l1-loss, straight off torch.nn.functional."""
    t = torch()
    registered = module_ops(m, t.nn.functional, ["mse_loss", "cross_entropy", "l1_loss"])
    LOSS_OPS[:] = registered
    return registered


def attach_optimizer(m, optimizer, name: str = "optim"):
    """(name-step!) and (name-zero!): the optimizer's own methods as
    operations, effect convention included (a Python None answers True, the
    engine's own spelling for an effectful builtin)."""
    wrap_object(
        m,
        name,
        optimizer,
        {"step": f"{name}-step!", "zero_grad": f"{name}-zero!"},
    )
    return optimizer


def train_step(m, loss_function: str, optimizer, *batch) -> float:
    """One update where the forward pass is MeTTa: returns the loss value.

    What to compute stays equations the engine can match, derive and
    explain; how to differentiate it is torch's.
    """
    t = torch()
    answers = m.eval(expr(S[loss_function], *batch))
    if len(answers) != 1:
        raise RuntimeError(
            f"({loss_function} ...) answered {len(answers)} results; "
            f"a training step needs exactly one loss tensor"
        )
    loss = answers[0]
    loss = loss.value if hasattr(loss, "value") else loss
    if not isinstance(loss, t.Tensor):
        raise RuntimeError(f"({loss_function} ...) answered {loss!r}, not a tensor")
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    return float(loss.item())
