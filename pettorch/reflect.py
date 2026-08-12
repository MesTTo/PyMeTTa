"""Purpose: nn.Module architecture as MeTTa knowledge, registered as a
reflector on the general reflection registry: wrap() and reflect() dispatch
through petta.integrate, and this module only teaches it what a torch module
looks like inside.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: fact vocabularies for more layer families (Conv,
    attention) as programs need them; Linear covers the demos today.
"""

from __future__ import annotations

from petta import S, expr, val
from petta import integrate as _integrate

from ._torch import torch

__all__ = ["reflect", "VOCABULARY", "register"]

VOCABULARY = [
    "(nn-module <name> <TypeSymbol>)",
    "(nn-child <parent-name> <child-name> <full-name>)",
    "(nn-param <module-name> <param-name> <tensor>)",
    "(nn-param-shape <module-name> <param-name> (<dim>...))",
    "(nn-linear <module-name> <in-features> <out-features>)",
]

_REGISTERED = False


def register() -> None:
    """Teach the general reflection registry about nn.Module, once."""
    global _REGISTERED
    if _REGISTERED:
        return
    t = torch()
    _integrate.register_reflector(lambda obj: isinstance(obj, t.nn.Module), _reflect_module)
    _REGISTERED = True


def reflect(m, root_name: str, module) -> int:
    """Write the module's architecture into the space; returns the fact count.

    Dispatches through the general registry, so pettorch.reflect and
    petta.integrate.reflect are the same call once register() has run.
    """
    register()
    return _integrate.reflect(m, root_name, module)


def _qualified(root: str, path: str) -> str:
    return root if not path else f"{root}.{path}"


def _reflect_module(m, root_name: str, module) -> int:
    t = torch()
    count = 0

    def add(atom) -> None:
        nonlocal count
        m.add(atom)
        count += 1

    for path, sub in module.named_modules():
        name = _qualified(root_name, path)
        add(expr(S["nn-module"], S[name], S[type(sub).__name__]))
        for child_name, _child in sub.named_children():
            add(expr(S["nn-child"], S[name], S[child_name], S[_qualified(name, child_name)]))
        for param_name, param in sub.named_parameters(recurse=False):
            add(expr(S["nn-param"], S[name], S[param_name], val(param)))
            add(expr(S["nn-param-shape"], S[name], S[param_name], expr(*list(param.shape))))
        if isinstance(sub, t.nn.Linear):
            add(expr(S["nn-linear"], S[name], sub.in_features, sub.out_features))
    return count
