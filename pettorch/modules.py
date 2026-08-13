"""Purpose: the two directions a model crosses the boundary, built on the
general interface. wrap() is petta.integrate.wrap_callable plus the nn.Module
reflector; MettaModule packages a MeTTa forward pass as an nn.Module so it
slots into optimizers and training loops, its parameters reached from MeTTa
through an ordinary registered operation. The autograd graph survives
because tensors cross by identity, a property of the boundary, not of torch.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any

from petta import Gnd, S, decode, expr, val
from petta.integrate import wrap_callable

from .reflect import reflect as _reflect_model
from ._torch import torch

__all__ = ["wrap", "MettaModule"]

# Whose parameters (param ...) answers with. During a forward pass, the
# running module's, top of the stack, so two models never read each other's
# weights however many exist. Outside any forward, the module built on the
# space the engine is evaluating in, read through petta.current_space();
# only when that still leaves several is the read ambiguous, and it says so.
_ACTIVE: list[dict[str, Any]] = []
_BY_OP: dict[tuple[str, str], list[dict[str, Any]]] = {}
_REGISTERED_OPS: set[str] = set()


def wrap(m, name: str, module, *, arities: list[int] | None = None):
    """Register a model (or any callable over tensors) as a MeTTa function.

        pettorch.wrap(m, "classify", model)
        m.run("!(t-argmax (classify (tensor (1.0 2.0))))")

    An nn.Module also reflects its architecture into facts and lands as
    (nn-wrapped name <module>), so rules route between models symbolically.
    """
    t = torch()
    wrap_callable(m, name, module, arities=arities or [1])
    m.add(expr(S["nn-wrapped"], S[name], val(module)))
    if isinstance(module, t.nn.Module):
        _reflect_model(m, name, module)
    return module


def MettaModule(metta, function: str, params: dict[str, Any] | None = None,
                param_op: str = "param"):
    """An nn.Module whose forward pass is a MeTTa program.

        m.run("(= (predict $x) (t-sum (t* (param w) $x)))")
        model = pettorch.MettaModule(m, "predict", params={"w": torch.zeros(2)})
        optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
        loss = loss_fn(model(x), target)   # forward runs the equations
        loss.backward()                    # gradients reach model.w

    Parameters are ordinary nn.Parameters registered on the module, reached
    from MeTTa through (param name) as the very same objects, which is what
    keeps the graph connected. torch.compile cannot trace through the
    engine; forward runs eager. A factory rather than a class, so importing
    pettorch never imports torch.
    """
    t = torch()

    class _MettaModule(t.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self._function = function
            registry: dict[str, t.nn.Parameter] = {}
            for name, tensor in (params or {}).items():
                parameter = (
                    tensor
                    if isinstance(tensor, t.nn.Parameter)
                    else t.nn.Parameter(tensor.detach().clone())
                )
                self.register_parameter(name, parameter)
                registry[name] = parameter
            self._registry = registry
            _BY_OP.setdefault((param_op, metta.space_name), []).append(registry)

            if param_op not in _REGISTERED_OPS:

                def fetch(key) -> Any:
                    from petta.space import current_space

                    name = key.name if hasattr(key, "name") else str(key)
                    if _ACTIVE:
                        owner = _ACTIVE[-1]
                    else:
                        space = current_space()
                        owners = _BY_OP.get((param_op, space), [])
                        if len(owners) != 1:
                            raise RuntimeError(
                                f"({param_op} {name}) is ambiguous here: "
                                f"{len(owners)} modules built on {space} "
                                f"share the operation. Evaluate through the "
                                f"module, or give each its own param_op."
                            )
                        owner = owners[0]
                    if name not in owner:
                        raise KeyError(
                            f"({param_op} {name}) names no parameter here; "
                            f"parameters are {sorted(owner)}"
                        )
                    return val(owner[name])

                metta.op(fetch, name=param_op, raw=False, typed=False, pass_atoms=True)
                _REGISTERED_OPS.add(param_op)

        def forward(self, *xs):
            _ACTIVE.append(self._registry)
            try:
                answers = metta.eval(expr(S[function], *(val(x) for x in xs)))
            finally:
                _ACTIVE.pop()
            if len(answers) != 1:
                raise RuntimeError(
                    f"({function} ...) answered {len(answers)} results; a "
                    f"forward pass needs exactly one. Reduce nondeterminism "
                    f"inside MeTTa, with collapse and a choice, first."
                )
            answer = answers[0]
            value = decode(answer) if isinstance(answer, Gnd) else answer
            if not isinstance(value, t.Tensor):
                raise RuntimeError(
                    f"({function} ...) answered {answer}, not a tensor; a "
                    f"MettaModule forward must produce one tensor."
                )
            return value

        def extra_repr(self) -> str:
            return f"function={function!r}, space={metta.space_name!r}"

    _MettaModule.__name__ = "MettaModule"
    _MettaModule.__qualname__ = "MettaModule"
    return _MettaModule()
