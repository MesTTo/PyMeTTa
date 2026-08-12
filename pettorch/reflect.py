"""Purpose: an nn.Module's architecture as MeTTa knowledge. reflect() lowers
the module tree into facts a program can match on: submodules and their
types, parameters with shapes, and Linear layer dimensions, so rules find
layers, check shape compatibility and select submodules symbolically.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: fact vocabularies for more layer families (Conv,
    attention) as programs need them; Linear covers the demos today.
"""

from __future__ import annotations

from petta import S, expr, val

from ._torch import torch

__all__ = ["reflect", "VOCABULARY"]

# The fact shapes reflect() writes, documented as data so a program can ask.
VOCABULARY = [
    "(nn-module <name> <TypeSymbol>)",
    "(nn-child <parent-name> <child-name> <full-name>)",
    "(nn-param <module-name> <param-name> <tensor>)",
    "(nn-param-shape <module-name> <param-name> (<dim>...))",
    "(nn-linear <module-name> <in-features> <out-features>)",
]


def _qualified(root: str, path: str) -> str:
    return root if not path else f"{root}.{path}"


def reflect(m, root_name: str, module) -> int:
    """Write the module's architecture into the space; returns the fact count.

        pettorch.reflect(m, "net", model)
        m.query("(nn-linear $layer $in $out)")

    Facts follow VOCABULARY. Parameter facts carry the live tensor, the same
    object the module trains, so a rule can hand a parameter straight to an
    optimizer step or a gradient read.
    """
    t = torch()
    if not isinstance(module, t.nn.Module):
        raise TypeError(f"reflect expects an nn.Module, got {type(module).__name__}")
    count = 0

    def add(atom) -> None:
        nonlocal count
        m.add(atom)
        count += 1

    for path, sub in module.named_modules():
        name = _qualified(root_name, path)
        add(expr(S["nn-module"], S[name], S[type(sub).__name__]))
        for child_name, _child in sub.named_children():
            add(
                expr(
                    S["nn-child"],
                    S[name],
                    S[child_name],
                    S[_qualified(name, child_name)],
                )
            )
        for param_name, param in sub.named_parameters(recurse=False):
            add(expr(S["nn-param"], S[name], S[param_name], val(param)))
            add(
                expr(
                    S["nn-param-shape"],
                    S[name],
                    S[param_name],
                    expr(*list(param.shape)),
                )
            )
        if isinstance(sub, t.nn.Linear):
            add(expr(S["nn-linear"], S[name], sub.in_features, sub.out_features))
    return count
