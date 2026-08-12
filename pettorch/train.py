"""Purpose: training as MeTTa. Loss functions as MeTTa operations, an
optimizer attached as step and zero operations, and a train_step helper that
runs one whole update through the engine: forward by equations, backward and
step in torch, loss returned as a number.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from petta import S, expr

from ._torch import torch

__all__ = ["install_loss_ops", "attach_optimizer", "train_step", "LOSS_OPS"]

LOSS_OPS: list[str] = []


def install_loss_ops(m) -> list[str]:
    """Register the loss functions install() ships: mse, cross-entropy, l1."""
    t = torch()
    registered = []

    def op(fn, name):
        m.op(fn, name=name, raw=True, typed=False)
        registered.append(name)

    op(lambda pred, target: t.nn.functional.mse_loss(pred, target), "mse-loss")
    op(
        lambda logits, target: t.nn.functional.cross_entropy(logits, target),
        "cross-entropy",
    )
    op(lambda pred, target: t.nn.functional.l1_loss(pred, target), "l1-loss")
    LOSS_OPS[:] = registered
    return registered


def attach_optimizer(m, optimizer, name: str = "optim"):
    """Give an optimizer MeTTa spellings: (<name>-step!) and (<name>-zero!).

        opt = torch.optim.SGD(model.parameters(), lr=0.1)
        pettorch.attach_optimizer(m, opt)
        m.run("!(optim-zero!)")     # zero gradients
        ...backward...
        m.run("!(optim-step!)")     # apply the update

    Both answer True, the engine's own convention for an effectful builtin.
    """

    def step() -> bool:
        optimizer.step()
        return True

    def zero() -> bool:
        optimizer.zero_grad()
        return True

    m.op(step, name=f"{name}-step!", raw=True, typed=False)
    m.op(zero, name=f"{name}-zero!", raw=True, typed=False)
    return optimizer


def train_step(m, loss_function: str, optimizer, *batch) -> float:
    """One update where the forward pass is MeTTa: returns the loss value.

    Evaluates (loss_function batch...) in the space, which must answer one
    loss tensor; then zero_grad, backward and step here. The division of
    labour is the point: what to compute is equations the engine can match,
    derive and explain; how to differentiate it is torch's.
    """
    t = torch()
    call = expr(S[loss_function], *batch)
    answers = m.eval(call)
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
