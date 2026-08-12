"""Purpose: the tensor operation set install() registers: constructors,
algebra, shape work, reductions, activations, autograd controls and the exits
back to MeTTa data. Tensors cross as object references with identity, so
every operation composes with equations, match, superpose and collapse, and
the autograd graph survives the engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from petta import Expr, Gnd, S, decode, expr, val
from petta.atoms import Atom

from ._torch import torch

__all__ = ["install_tensor_ops", "TENSOR_OPS", "atom_to_data"]

# Filled by install_tensor_ops: every MeTTa name this module registered.
TENSOR_OPS: list[str] = []


def atom_to_data(a: Any) -> Any:
    """Nested expression of numbers to nested Python lists; values pass through."""
    if isinstance(a, Expr):
        return [atom_to_data(c) for c in a]
    if isinstance(a, Gnd):
        return decode(a)
    if isinstance(a, Atom):
        raise TypeError(f"tensor data may not contain {a.metatype}: {a}")
    return a


def _declare(m, name: str, arrow: list[str]) -> None:
    """(: name (-> ...)) so get-type answers for tensor work."""
    m.add(expr(S[":"], S[name], Expr([S["->"], *(S[t] for t in arrow)])))


def install_tensor_ops(m) -> list[str]:
    """Register the op set on the shared engine; returns the names."""
    t = torch()
    registered: list[str] = []

    def op(fn, *, name: str, raw: bool = True, types: list[str] | None = None, **kw):
        if m.is_function(name) and name not in _known_ops():
            raise ValueError(
                f"refusing to register {name!r}: the engine already has a "
                f"function by that name and it is not a pettorch operation"
            )
        m.op(fn, name=name, raw=raw, typed=False, **kw)
        if types:
            _declare(m, name, types)
        registered.append(name)
        return fn

    # ------------------------------------------------------------ constructors

    def make_tensor(data) -> Any:
        if isinstance(data, t.Tensor):
            return val(data)
        return val(t.tensor(atom_to_data(data), dtype=t.float32))

    # The data argument may be an expression or a single number, so the input
    # stays undeclared; the output really is checked against the object's own
    # Python classes, which is what makes Tensor a true type here.
    op(make_tensor, name="tensor", raw=False, pass_atoms=True,
       types=["%Undefined%", "Tensor"])

    dims = [1, 2, 3, 4]
    op(lambda *shape: t.zeros(*[int(s) for s in shape]), name="zeros", arities=dims)
    op(lambda *shape: t.ones(*[int(s) for s in shape]), name="ones", arities=dims)
    op(lambda *shape: t.randn(*[int(s) for s in shape]), name="randn", arities=dims)
    op(lambda n: t.arange(float(n)), name="arange-t")
    op(lambda n: t.eye(int(n)), name="eye")

    # ---------------------------------------------------------------- algebra

    op(lambda a, b: t.matmul(a, b), name="matmul", types=["Tensor", "Tensor", "Tensor"])
    op(lambda a, b: a + b, name="t+", types=["Tensor", "Tensor", "Tensor"])
    op(lambda a, b: a - b, name="t-", types=["Tensor", "Tensor", "Tensor"])
    op(lambda a, b: a * b, name="t*", types=["Tensor", "Tensor", "Tensor"])
    op(lambda a, b: a / b, name="t/", types=["Tensor", "Tensor", "Tensor"])
    op(lambda a: -a, name="t-neg")
    op(lambda a: t.exp(a), name="t-exp")
    op(lambda a: t.log(a), name="t-log")
    op(lambda a, p: a ** p, name="t-pow")

    # ------------------------------------------------------------------ shape

    op(lambda a, *ds: a.reshape(*[int(d) for d in ds]), name="reshape",
       arities=[2, 3, 4, 5])
    op(lambda a, d0, d1: a.transpose(int(d0), int(d1)), name="t-transpose")
    op(lambda a, d: a.unsqueeze(int(d)), name="unsqueeze")
    op(lambda a, d: a.squeeze(int(d)), name="squeeze")
    op(lambda a, i: a[int(i)], name="t-index")

    def cat_op(tensors, dim=0):
        return val(t.cat([decode(c) for c in tensors], dim=int(decode(dim))))

    def stack_op(tensors, dim=0):
        return val(t.stack([decode(c) for c in tensors], dim=int(decode(dim))))

    op(cat_op, name="cat", raw=False, pass_atoms=True)
    op(stack_op, name="stack", raw=False, pass_atoms=True)

    # ------------------------------------------------------------- reductions

    op(lambda a: t.sum(a), name="t-sum", types=["Tensor", "Tensor"])
    op(lambda a: t.mean(a), name="t-mean")
    op(lambda a: t.max(a), name="t-max")
    op(lambda a: t.min(a), name="t-min")
    op(lambda a, dim=-1: int(t.argmax(a, dim=int(dim)).item())
       if a.dim() <= 1 else t.argmax(a, dim=int(dim)),
       name="t-argmax")
    op(lambda a: t.linalg.norm(a), name="t-norm")

    # ------------------------------------------------------------ activations

    op(lambda a: t.relu(a), name="relu", types=["Tensor", "Tensor"])
    op(lambda a: t.sigmoid(a), name="sigmoid")
    op(lambda a, dim=-1: t.softmax(a, dim=int(dim)), name="softmax",
       types=["Tensor", "Tensor"])
    op(lambda a: t.tanh(a), name="tanh")
    op(lambda a: t.nn.functional.gelu(a), name="gelu")

    # --------------------------------------------------------------- autograd

    op(lambda a: a.requires_grad_(True), name="t-requires-grad!")
    op(lambda a: a.detach(), name="t-detach")

    def backward(a) -> bool:
        a.backward()
        return True

    op(backward, name="t-backward!")

    def grad(a):
        # Semidet: a parameter that has no gradient yet answers nothing.
        return a.grad if a.grad is not None else None

    op(grad, name="t-grad")

    # ------------------------------------------------------------------ exits

    op(lambda a: a.item(), name="t-item", types=["Tensor", "Number"])

    def tolist(a) -> Any:
        data = decode(a).tolist()
        return expr(*data) if isinstance(data, list) else data

    op(tolist, name="t-tolist", raw=False, types=["Tensor", "Expression"])

    def shape(a) -> Any:
        return expr(*list(decode(a).shape))

    op(shape, name="t-shape", raw=False, types=["Tensor", "Expression"])

    op(lambda a: str(a.dtype).removeprefix("torch."), name="t-dtype")
    op(lambda a: str(a.device), name="t-device")
    op(lambda a, target: a.to(target), name="t-to")

    TENSOR_OPS[:] = registered
    return registered


def _known_ops() -> set[str]:
    from petta._ops import REGISTRY

    return set(REGISTRY)
