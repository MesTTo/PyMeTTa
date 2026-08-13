"""Purpose: DeepProbLog's neural predicate on this engine: a probabilistic
relation whose distribution a network parameterizes (Manhaeve et al.,
"DeepProbLog: Neural Probabilistic Logic Programming", NeurIPS 2018). Where
DeepProbLog writes nn(m, [X], Y, domain) :: digit(X, Y), here
neural_predicate(m, "digit", network, classes) registers (digit $x) as a
nondeterministic function answering (probability class) pairs from the
softmaxed forward pass, and (digit $x $class) as the bound mode scoring one
class. The relation itself is petta.measure.weighted_relation, the general
weighted-relation mechanism; this module contributes exactly what is torch:
the forward pass, the softmax, and the with_grad choice between crossing
probabilities as floats or as 0-d tensors on the autograd graph.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Iterable

from petta.atoms import Gnd, decode
from petta.measure import weighted_relation

from ._torch import torch

__all__ = ["neural_predicate"]


def neural_predicate(
    m,
    name: str,
    network: Any,
    classes: Iterable[Any],
    *,
    with_grad: bool = False,
) -> str:
    """Register a network as a neural predicate under one MeTTa name.

        pettorch.neural_predicate(m, "digit", classifier, range(10))
        m.run("!(ws-best (collapse (digit (tensor (...)))))")   # argmax class
        m.run("!(digit (tensor (...)) 7)")                      # (p7 7)

    classes are the relation's answer terms, one output logit each, in
    order. Probabilities cross as floats for reasoning; with_grad=True
    keeps them as 0-d tensors on the autograd graph, the DeepProbLog
    training reading, at the price that only tensor operations may touch
    them downstream.
    """
    t = torch()

    def distribution(value: Any):
        tensor = decode(value) if isinstance(value, Gnd) else value
        if not isinstance(tensor, t.Tensor):
            raise TypeError(
                f"({name} ...) takes a tensor input, got {type(tensor).__name__}"
            )
        if with_grad:
            probabilities = t.softmax(network(tensor).reshape(-1), dim=0)
        else:
            with t.no_grad():
                probabilities = t.softmax(network(tensor).reshape(-1), dim=0)
        return [_carry(p, with_grad) for p in probabilities]

    return weighted_relation(m, name, distribution, classes)


def _carry(probability: Any, with_grad: bool) -> Any:
    from petta import val

    return val(probability) if with_grad else float(probability)
